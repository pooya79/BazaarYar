from __future__ import annotations

import io
import json
import mimetypes
import os
import shutil
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

os.environ.setdefault("XDG_CONFIG_HOME", "/tmp")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

WORKSPACE_DIR = Path("/workspace")
STATE_DIR = WORKSPACE_DIR / "state"
INPUT_DIR = WORKSPACE_DIR / "input"
OUTPUT_DIR = WORKSPACE_DIR / "output"
REQUESTS_DIR = WORKSPACE_DIR / "requests"
RESPONSES_DIR = WORKSPACE_DIR / "responses"
RESPONSE_ARTIFACTS_DIR = WORKSPACE_DIR / "response_artifacts"
INPUT_MANIFEST_PATH = STATE_DIR / "input_manifest.json"
READY_PATH = STATE_DIR / "runner.ready"
POLL_SECONDS = 0.05
STDOUT_TAIL_LIMIT = 8_000
STDERR_TAIL_LIMIT = 8_000
TRACEBACK_TAIL_LIMIT = 8_000
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}


def _emit(payload: dict[str, Any]) -> None:
    sys.__stdout__.write(f"{json.dumps(payload, ensure_ascii=True)}\n")
    sys.__stdout__.flush()


def _tail(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"...{value[-limit:]}"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    os.replace(tmp, path)


def _load_input_manifest() -> list[dict[str, str]]:
    if not INPUT_MANIFEST_PATH.exists():
        return []
    try:
        raw = json.loads(INPUT_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []

    manifest: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sandbox_filename = str(item.get("sandbox_filename") or "").strip()
        if not sandbox_filename:
            continue
        manifest.append(
            {
                "attachment_id": str(item.get("attachment_id") or "").strip(),
                "original_filename": str(item.get("original_filename") or sandbox_filename).strip(),
                "sandbox_filename": sandbox_filename,
                "content_type": str(item.get("content_type") or "application/octet-stream").strip(),
                "input_path": str(item.get("input_path") or f"/workspace/input/{sandbox_filename}").strip(),
            }
        )
    return manifest


def _available_files(input_files: list[dict[str, str]]) -> list[str]:
    return [item["sandbox_filename"] for item in input_files if item.get("sandbox_filename")]


def _output_fingerprint() -> dict[Path, tuple[int, int]]:
    if not OUTPUT_DIR.exists():
        return {}
    fingerprint: dict[Path, tuple[int, int]] = {}
    for path in OUTPUT_DIR.rglob("*"):
        if not path.is_file():
            continue
        stat = path.stat()
        fingerprint[path.resolve()] = (stat.st_mtime_ns, stat.st_size)
    return fingerprint


def _is_image_file(path: Path) -> bool:
    if path.suffix.lower() in _IMAGE_EXTENSIONS:
        return True
    mime_type = mimetypes.guess_type(path.name)[0] or ""
    return mime_type.startswith("image/")


def _has_new_image_artifact(*, before: dict[Path, tuple[int, int]], after: dict[Path, tuple[int, int]]) -> bool:
    for path in after:
        if path in before:
            continue
        if _is_image_file(path):
            return True
    return False


def _auto_save_open_figures() -> None:
    figure_numbers = sorted(plt.get_fignums())
    if not figure_numbers:
        return

    next_index = 1
    for figure_number in figure_numbers:
        while (OUTPUT_DIR / f"auto_plot_{next_index:02d}.png").exists():
            next_index += 1
        figure = plt.figure(figure_number)
        figure.savefig(
            OUTPUT_DIR / f"auto_plot_{next_index:02d}.png",
            format="png",
            bbox_inches="tight",
        )
        next_index += 1


def load_dataframe(name: str, **kwargs: Any) -> pd.DataFrame:
    path = (INPUT_DIR / name).resolve()
    if INPUT_DIR.resolve() not in path.parents:
        raise ValueError("File path escapes input directory")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input file '{name}' does not exist")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, **kwargs)
    if suffix in {".tsv", ".tab"}:
        if "sep" not in kwargs and "delimiter" not in kwargs:
            kwargs["sep"] = "\t"
        return pd.read_csv(path, **kwargs)
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(path, **kwargs)
    if suffix == ".json":
        return pd.read_json(path, **kwargs)

    raise ValueError(f"Unsupported dataframe file extension: {suffix}")


def _execute(
    code: str,
    *,
    globals_map: dict[str, Any],
    input_files: list[dict[str, str]],
) -> tuple[str, str]:
    globals_map["ATTACHMENTS"] = input_files
    globals_map["AVAILABLE_FILES"] = _available_files(input_files)
    globals_map["INPUT_DIR"] = INPUT_DIR
    globals_map["OUTPUT_DIR"] = OUTPUT_DIR
    globals_map["load_dataframe"] = load_dataframe

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    current_dir = Path.cwd()

    try:
        output_before = _output_fingerprint()
        os.chdir(OUTPUT_DIR)
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(compile(code, "sandbox_session_job.py", "exec"), globals_map, globals_map)
        output_after = _output_fingerprint()
        if not _has_new_image_artifact(before=output_before, after=output_after):
            _auto_save_open_figures()
    finally:
        os.chdir(current_dir)

    return stdout_buffer.getvalue(), stderr_buffer.getvalue()


def _collect_delta_artifacts(
    *,
    request_id: str,
    before: dict[Path, tuple[int, int]],
    after: dict[Path, tuple[int, int]],
) -> list[dict[str, str]]:
    changed_paths = sorted(path for path, fp in after.items() if before.get(path) != fp)
    if not changed_paths:
        return []

    request_artifacts_dir = RESPONSE_ARTIFACTS_DIR / request_id
    if request_artifacts_dir.exists():
        shutil.rmtree(request_artifacts_dir, ignore_errors=True)
    request_artifacts_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict[str, str]] = []
    for path in changed_paths:
        rel_path = path.relative_to(OUTPUT_DIR).as_posix()
        target = request_artifacts_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        artifacts.append(
            {
                "filename": path.name,
                "rel_path": rel_path,
                "content_type": content_type,
            }
        )
    return artifacts


def _next_request_path() -> Path | None:
    candidates = sorted(path for path in REQUESTS_DIR.glob("*.json") if path.is_file())
    if not candidates:
        return None
    return candidates[0]


def _process_request(request_path: Path, *, globals_map: dict[str, Any]) -> None:
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    request_id = str(request_payload.get("request_id") or "").strip()
    code = str(request_payload.get("code") or "")
    if not request_id:
        raise RuntimeError(f"Invalid request payload in {request_path.name}: missing request_id")

    response_path = RESPONSES_DIR / f"{request_id}.json"
    input_files = _load_input_manifest()
    output_before = _output_fingerprint()
    try:
        stdout_value, stderr_value = _execute(code, globals_map=globals_map, input_files=input_files)
        output_after = _output_fingerprint()
        artifacts = _collect_delta_artifacts(request_id=request_id, before=output_before, after=output_after)
        payload = {
            "request_id": request_id,
            "status": "succeeded",
            "summary": "Sandbox execution completed.",
            "stdout_tail": _tail(stdout_value, limit=STDOUT_TAIL_LIMIT),
            "stderr_tail": _tail(stderr_value, limit=STDERR_TAIL_LIMIT),
            "artifacts": artifacts,
            "error_message": None,
        }
    except Exception as exc:
        payload = {
            "request_id": request_id,
            "status": "failed",
            "summary": str(exc),
            "stdout_tail": "",
            "stderr_tail": _tail(traceback.format_exc(), limit=TRACEBACK_TAIL_LIMIT),
            "artifacts": [],
            "error_message": str(exc),
        }

    _atomic_write_json(response_path, payload)
    request_path.unlink(missing_ok=True)


def main() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    RESPONSE_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    READY_PATH.write_text("ready", encoding="utf-8")
    _emit({"type": "status", "stage": "ready", "message": "Sandbox session runner ready."})

    globals_map: dict[str, Any] = {
        "__name__": "__sandbox_session__",
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
    }

    while True:
        request_path = _next_request_path()
        if request_path is None:
            time.sleep(POLL_SECONDS)
            continue
        try:
            _process_request(request_path, globals_map=globals_map)
        except Exception as exc:  # pragma: no cover - defensive runner guard
            _emit(
                {
                    "type": "error",
                    "message": str(exc),
                    "traceback_tail": _tail(traceback.format_exc(), limit=TRACEBACK_TAIL_LIMIT),
                }
            )
            request_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
