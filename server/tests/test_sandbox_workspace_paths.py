from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from server.core.config import Settings, get_settings
from server.features.agent.sandbox.sandbox_executor import _sandbox_runs_root
from server.features.agent.sandbox.session_executor import _sandbox_sessions_root
from server.features.agent.sandbox.workspace_paths import (
    ensure_workspace_subdir,
    get_effective_workspace_root,
)
from server.features.agent.sandbox import workspace_paths


def test_settings_accepts_absolute_sandbox_workspace_root():
    settings = Settings.model_validate({"SANDBOX_WORKSPACE_ROOT": "/tmp/bazaaryar-sandbox"})
    assert settings.sandbox_workspace_root == "/tmp/bazaaryar-sandbox"


def test_settings_rejects_relative_sandbox_workspace_root():
    with pytest.raises(ValidationError, match="SANDBOX_WORKSPACE_ROOT must be an absolute path."):
        Settings.model_validate({"SANDBOX_WORKSPACE_ROOT": "tmp/bazaaryar-sandbox"})


def test_sandbox_roots_use_configured_workspace_root(monkeypatch, tmp_path: Path):
    workspace_root = tmp_path / "sandbox-root"
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "sandbox_workspace_root", str(workspace_root))

    runs_root = _sandbox_runs_root()
    sessions_root = _sandbox_sessions_root()

    assert runs_root == workspace_root / "runs"
    assert sessions_root == workspace_root / "sessions"
    assert runs_root.is_dir()
    assert sessions_root.is_dir()


def test_unwritable_root_falls_back_to_per_user_tmp_in_development(monkeypatch, tmp_path: Path):
    configured_root = tmp_path / "configured"
    configured_root.mkdir(parents=True, exist_ok=True)
    fallback_root = tmp_path / "fallback"

    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "sandbox_workspace_root", str(configured_root))
    monkeypatch.setattr(workspace_paths, "_fallback_workspace_root", lambda: fallback_root)

    original_access = workspace_paths.os.access

    def _fake_access(path: object, mode: int) -> bool:
        if Path(path) == configured_root:
            return False
        return original_access(path, mode)

    monkeypatch.setattr(workspace_paths.os, "access", _fake_access)

    runs_root = _sandbox_runs_root()
    sessions_root = _sandbox_sessions_root()

    assert runs_root == fallback_root / "runs"
    assert sessions_root == fallback_root / "sessions"
    assert runs_root.is_dir()
    assert sessions_root.is_dir()


def test_unwritable_root_fails_fast_in_production(monkeypatch, tmp_path: Path):
    configured_root = tmp_path / "configured"
    configured_root.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "sandbox_workspace_root", str(configured_root))

    original_access = workspace_paths.os.access

    def _fake_access(path: object, mode: int) -> bool:
        if Path(path) == configured_root:
            return False
        return original_access(path, mode)

    monkeypatch.setattr(workspace_paths.os, "access", _fake_access)

    with pytest.raises(PermissionError, match="SANDBOX_WORKSPACE_ROOT"):
        get_effective_workspace_root()


def test_ensure_workspace_subdir_creates_runs_and_sessions(monkeypatch, tmp_path: Path):
    configured_root = tmp_path / "sandbox-root"
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "sandbox_workspace_root", str(configured_root))

    runs_root = ensure_workspace_subdir("runs")
    sessions_root = ensure_workspace_subdir("sessions")

    assert runs_root == configured_root / "runs"
    assert sessions_root == configured_root / "sessions"
    assert runs_root.is_dir()
    assert sessions_root.is_dir()


def test_chmod_permission_error_does_not_crash_root_resolution(monkeypatch, tmp_path: Path):
    configured_root = tmp_path / "sandbox-root"
    configured_root.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "sandbox_workspace_root", str(configured_root))

    def _raise_permission_error(_self: Path, _mode: int, *, follow_symlinks: bool = True) -> None:
        raise PermissionError("simulated chmod error")

    monkeypatch.setattr(workspace_paths.Path, "chmod", _raise_permission_error)

    runs_root = ensure_workspace_subdir("runs")
    assert runs_root == configured_root / "runs"
    assert runs_root.is_dir()
