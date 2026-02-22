from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from server.core.config import Settings, get_settings
from server.features.agent.sandbox.sandbox_executor import _sandbox_runs_root
from server.features.agent.sandbox.session_executor import _sandbox_sessions_root


def test_settings_accepts_absolute_sandbox_workspace_root():
    settings = Settings.model_validate({"SANDBOX_WORKSPACE_ROOT": "/tmp/bazaaryar-sandbox"})
    assert settings.sandbox_workspace_root == "/tmp/bazaaryar-sandbox"


def test_settings_rejects_relative_sandbox_workspace_root():
    with pytest.raises(ValidationError, match="SANDBOX_WORKSPACE_ROOT must be an absolute path."):
        Settings.model_validate({"SANDBOX_WORKSPACE_ROOT": "tmp/bazaaryar-sandbox"})


def test_sandbox_roots_use_configured_workspace_root(monkeypatch, tmp_path: Path):
    workspace_root = tmp_path / "sandbox-root"
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_workspace_root", str(workspace_root))

    runs_root = _sandbox_runs_root()
    sessions_root = _sandbox_sessions_root()

    assert runs_root == workspace_root / "runs"
    assert sessions_root == workspace_root / "sessions"
    assert runs_root.is_dir()
    assert sessions_root.is_dir()
