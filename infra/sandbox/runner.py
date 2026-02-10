from __future__ import annotations

import io
import json
import mimetypes
import os
import sys
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
JOB_PATH = WORKSPACE_DIR / "job.json"
INPUT_DIR = WORKSPACE_DIR / "input"
OUTPUT_DIR = WORKSPACE_DIR / "output"
STDOUT_TAIL_LIMIT = 8000
STDERR_TAIL_LIMIT = 8000
TRACEBACK_TAIL_LIMIT = 8000
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}


def _emit(payload: dict[str, Any]) -> None:
    sys.__stdout__.write(f"{json.dumps(payload, ensure_ascii=True)}\n")
    sys.__stdout__.flush()


def _tail(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"...{value[-limit:]}"


def _load_job() -> dict[str, Any]:
    if not JOB_PATH.exists():
        raise RuntimeError("Missing /workspace/job.json")
    try:
        return json.loads(JOB_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Invalid job payload: {exc}") from exc


def _normalize_input_manifest(job: dict[str, Any]) -> list[dict[str, str]]:
    raw_manifest = job.get("input_files")
    if isinstance(raw_manifest, list):
        manifest: list[dict[str, str]] = []
        for raw_item in raw_manifest:
            if not isinstance(raw_item, dict):
                continue
            sandbox_filename = str(raw_item.get("sandbox_filename") or "").strip()
            if not sandbox_filename:
                continue
            input_path = str(raw_item.get("input_path") or f"/workspace/input/{sandbox_filename}").strip()
            manifest.append(
                {
                    "attachment_id": str(raw_item.get("attachment_id") or "").strip(),
                    "original_filename": str(raw_item.get("original_filename") or sandbox_filename).strip(),
                    "sandbox_filename": sandbox_filename,
                    "content_type": str(raw_item.get("content_type") or "application/octet-stream").strip(),
                    "input_path": input_path,
                }
            )
        return manifest

    raw_files = job.get("files")
    if not isinstance(raw_files, list):
        return []

    fallback_manifest: list[dict[str, str]] = []
    for raw_name in raw_files:
        sandbox_filename = str(raw_name or "").strip()
        if not sandbox_filename:
            continue
        fallback_manifest.append(
            {
                "attachment_id": "",
                "original_filename": sandbox_filename,
                "sandbox_filename": sandbox_filename,
                "content_type": "application/octet-stream",
                "input_path": f"/workspace/input/{sandbox_filename}",
            }
        )
    return fallback_manifest


def _available_files(input_files: list[dict[str, str]]) -> list[str]:
    return [item["sandbox_filename"] for item in input_files if item.get("sandbox_filename")]


def _output_files() -> set[Path]:
    if not OUTPUT_DIR.exists():
        return set()
    return {path.resolve() for path in OUTPUT_DIR.rglob("*") if path.is_file()}


def _is_image_file(path: Path) -> bool:
    if path.suffix.lower() in _IMAGE_EXTENSIONS:
        return True
    mime_type = mimetypes.guess_type(path.name)[0] or ""
    return mime_type.startswith("image/")


def _has_new_image_artifact(*, before: set[Path], after: set[Path]) -> bool:
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


def _collect_artifacts() -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    if not OUTPUT_DIR.exists():
        return artifacts

    for path in sorted(OUTPUT_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(OUTPUT_DIR).as_posix()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        artifacts.append(
            {
                "filename": path.name,
                "rel_path": rel_path,
                "content_type": content_type,
            }
        )
    return artifacts


def _execute(code: str, *, input_files: list[dict[str, str]]) -> tuple[str, str]:
    globals_map: dict[str, Any] = {
        "__name__": "__sandbox__",
        "INPUT_DIR": INPUT_DIR,
        "OUTPUT_DIR": OUTPUT_DIR,
        "ATTACHMENTS": input_files,
        "AVAILABLE_FILES": _available_files(input_files),
        "load_dataframe": load_dataframe,
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
    }

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    current_dir = Path.cwd()

    try:
        # Force relative output paths (e.g. "output.png") into the writable artifacts directory.
        output_before = _output_files()
        os.chdir(OUTPUT_DIR)
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(compile(code, "sandbox_job.py", "exec"), globals_map, globals_map)
        output_after = _output_files()
        if not _has_new_image_artifact(before=output_before, after=output_after):
            _auto_save_open_figures()
    finally:
        os.chdir(current_dir)

    return stdout_buffer.getvalue(), stderr_buffer.getvalue()


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _emit({"type": "status", "stage": "initializing", "message": "Sandbox runner started."})

    try:
        job = _load_job()
    except Exception as exc:
        _emit(
            {
                "type": "error",
                "message": str(exc),
                "traceback_tail": _tail(traceback.format_exc(), limit=TRACEBACK_TAIL_LIMIT),
            }
        )
        return 1

    code = str(job.get("code") or "")
    input_files = _normalize_input_manifest(job)
    _emit(
        {
            "type": "status",
            "stage": "executing",
            "message": "Executing Python code.",
        }
    )

    try:
        stdout_value, stderr_value = _execute(code, input_files=input_files)
    except Exception as exc:
        _emit(
            {
                "type": "error",
                "message": str(exc),
                "traceback_tail": _tail(traceback.format_exc(), limit=TRACEBACK_TAIL_LIMIT),
            }
        )
        return 1

    _emit(
        {
            "type": "status",
            "stage": "collecting_artifacts",
            "message": "Collecting output artifacts.",
        }
    )

    _emit(
        {
            "type": "result",
            "stdout_tail": _tail(stdout_value, limit=STDOUT_TAIL_LIMIT),
            "stderr_tail": _tail(stderr_value, limit=STDERR_TAIL_LIMIT),
            "artifacts": _collect_artifacts(),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
