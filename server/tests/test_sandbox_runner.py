from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from uuid import uuid4

import pytest


def _load_runner_module():
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    pytest.importorskip("seaborn")
    runner_path = Path(__file__).resolve().parents[2] / "infra" / "sandbox" / "runner.py"
    module_name = f"sandbox_runner_test_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load sandbox runner module for testing.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_session_runner_module():
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    pytest.importorskip("seaborn")
    runner_path = Path(__file__).resolve().parents[2] / "infra" / "sandbox" / "session_runner.py"
    module_name = f"sandbox_session_runner_test_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load sandbox session runner module for testing.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_auto_saves_plot_when_no_explicit_image(tmp_path: Path):
    runner = _load_runner_module()
    runner.INPUT_DIR = tmp_path / "input"
    runner.OUTPUT_DIR = tmp_path / "output"
    runner.INPUT_DIR.mkdir(parents=True, exist_ok=True)
    runner.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    runner.plt.close("all")

    runner._execute(
        "plt.figure(); plt.plot([1, 2], [3, 4]); print('done')",
        input_files=[],
    )
    artifacts = runner._collect_artifacts()
    runner.plt.close("all")

    filenames = [item["filename"] for item in artifacts]
    assert any(name.startswith("auto_plot_") and name.endswith(".png") for name in filenames)


def test_runner_does_not_create_auto_plot_when_explicit_plot_exists(tmp_path: Path):
    runner = _load_runner_module()
    runner.INPUT_DIR = tmp_path / "input"
    runner.OUTPUT_DIR = tmp_path / "output"
    runner.INPUT_DIR.mkdir(parents=True, exist_ok=True)
    runner.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    runner.plt.close("all")

    runner._execute(
        "plt.figure(); plt.plot([1, 2], [3, 4]); plt.savefig('explicit_plot.png'); print('done')",
        input_files=[],
    )
    artifacts = runner._collect_artifacts()
    runner.plt.close("all")

    filenames = [item["filename"] for item in artifacts]
    assert "explicit_plot.png" in filenames
    assert not any(name.startswith("auto_plot_") for name in filenames)


def _configure_session_runner_dirs(session_runner, tmp_path: Path) -> None:
    session_runner.WORKSPACE_DIR = tmp_path
    session_runner.STATE_DIR = tmp_path / "state"
    session_runner.INPUT_DIR = tmp_path / "input"
    session_runner.OUTPUT_DIR = tmp_path / "output"
    session_runner.REQUESTS_DIR = tmp_path / "requests"
    session_runner.RESPONSES_DIR = tmp_path / "responses"
    session_runner.RESPONSE_ARTIFACTS_DIR = tmp_path / "response_artifacts"
    session_runner.INPUT_MANIFEST_PATH = session_runner.STATE_DIR / "input_manifest.json"
    for path in (
        session_runner.STATE_DIR,
        session_runner.INPUT_DIR,
        session_runner.OUTPUT_DIR,
        session_runner.REQUESTS_DIR,
        session_runner.RESPONSES_DIR,
        session_runner.RESPONSE_ARTIFACTS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def test_session_runner_preserves_globals_between_requests(tmp_path: Path):
    session_runner = _load_session_runner_module()
    _configure_session_runner_dirs(session_runner, tmp_path)
    session_runner.plt.close("all")

    globals_map = {
        "__name__": "__sandbox_session__",
        "pd": session_runner.pd,
        "np": session_runner.np,
        "plt": session_runner.plt,
        "sns": session_runner.sns,
    }

    request_1 = session_runner.REQUESTS_DIR / "00000000000000000001_req-1.json"
    request_1.write_text(
        '{"request_id":"req-1","code":"x = 41\\nprint(x)"}',
        encoding="utf-8",
    )
    session_runner._process_request(request_1, globals_map=globals_map)

    request_2 = session_runner.REQUESTS_DIR / "00000000000000000002_req-2.json"
    request_2.write_text(
        '{"request_id":"req-2","code":"print(x + 1)"}',
        encoding="utf-8",
    )
    session_runner._process_request(request_2, globals_map=globals_map)
    session_runner.plt.close("all")

    response_payload = json.loads((session_runner.RESPONSES_DIR / "req-2.json").read_text(encoding="utf-8"))
    assert response_payload["status"] == "succeeded"
    assert "42" in response_payload["stdout_tail"]


def test_session_runner_picks_requests_in_fifo_filename_order(tmp_path: Path):
    session_runner = _load_session_runner_module()
    _configure_session_runner_dirs(session_runner, tmp_path)

    early = session_runner.REQUESTS_DIR / "00000000000000000001_req-1.json"
    late = session_runner.REQUESTS_DIR / "00000000000000000002_req-2.json"
    late.write_text('{"request_id":"req-2","code":"print(2)"}', encoding="utf-8")
    early.write_text('{"request_id":"req-1","code":"print(1)"}', encoding="utf-8")

    first = session_runner._next_request_path()
    assert first is not None
    assert first.name == early.name


def test_session_runner_snapshots_artifacts_per_request(tmp_path: Path):
    session_runner = _load_session_runner_module()
    _configure_session_runner_dirs(session_runner, tmp_path)

    globals_map = {
        "__name__": "__sandbox_session__",
        "pd": session_runner.pd,
        "np": session_runner.np,
        "plt": session_runner.plt,
        "sns": session_runner.sns,
    }

    request_1 = session_runner.REQUESTS_DIR / "00000000000000000001_req-1.json"
    request_1.write_text(
        '{"request_id":"req-1","code":"open(\\"shared.txt\\", \\"w\\", encoding=\\"utf-8\\").write(\\"first\\")"}',
        encoding="utf-8",
    )
    session_runner._process_request(request_1, globals_map=globals_map)

    request_2 = session_runner.REQUESTS_DIR / "00000000000000000002_req-2.json"
    request_2.write_text(
        '{"request_id":"req-2","code":"open(\\"shared.txt\\", \\"w\\", encoding=\\"utf-8\\").write(\\"second\\")"}',
        encoding="utf-8",
    )
    session_runner._process_request(request_2, globals_map=globals_map)

    snap_path = session_runner.RESPONSE_ARTIFACTS_DIR / "req-1" / "shared.txt"
    assert snap_path.exists()
    assert snap_path.read_text(encoding="utf-8") == "first"
    assert (session_runner.OUTPUT_DIR / "shared.txt").read_text(encoding="utf-8") == "second"
