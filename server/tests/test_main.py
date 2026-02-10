from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_background_sweeper_runs_cleanup_without_python_calls(monkeypatch):
    main = importlib.import_module("server.main")

    calls: list[int] = []

    class _FakeSessionCM:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, _exc_type, _exc, _tb):
            return False

    def _fake_session_local():
        return _FakeSessionCM()

    async def _fake_cleanup(_session):
        calls.append(1)

    async def _fake_dispose():
        return None

    monkeypatch.setattr(main, "AsyncSessionLocal", _fake_session_local)
    monkeypatch.setattr(main, "cleanup_stale_sandbox_sessions", _fake_cleanup)
    monkeypatch.setattr(main, "async_engine", SimpleNamespace(dispose=_fake_dispose))
    monkeypatch.setattr(main.settings, "sandbox_tool_enabled", True)
    monkeypatch.setattr(main.settings, "sandbox_persist_sessions", True)
    monkeypatch.setattr(main.settings, "sandbox_session_sweep_interval_seconds", 1)

    async with main.lifespan(main.app):
        await asyncio.sleep(0.05)

    assert calls
