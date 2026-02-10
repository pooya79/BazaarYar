from __future__ import annotations

import importlib.util
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
