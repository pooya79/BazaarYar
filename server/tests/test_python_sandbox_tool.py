from __future__ import annotations

import json
from contextlib import asynccontextmanager

import pytest

from server.agents import python_sandbox_tool as sandbox_tool
from server.agents.sandbox_schema import SandboxExecutionResult
from server.core.config import get_settings


@asynccontextmanager
async def _fake_session_cm():
    yield object()


@pytest.mark.asyncio
async def test_python_sandbox_tool_allows_no_explicit_intent_and_no_attachments(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_tool_enabled", True)
    monkeypatch.setattr(settings, "sandbox_max_code_chars", 20_000)

    async def _fake_load_attachments_for_ids(_session, attachment_ids, *, allow_json_fallback=True):
        _ = allow_json_fallback
        assert attachment_ids == []
        return []

    async def _fake_execute_sandbox(request, *, on_status=None):
        if on_status is not None:
            await on_status("executing", "Running sandbox")
        assert request.files == []
        return SandboxExecutionResult(
            run_id=request.run_id,
            status="succeeded",
            summary="Sandbox execution completed.",
            stdout_tail="ok",
            stderr_tail="",
            artifacts=[],
        )

    async def _fake_save_uploaded_attachments(_session, uploaded_files):
        assert uploaded_files == []
        return []

    monkeypatch.setattr(sandbox_tool, "AsyncSessionLocal", _fake_session_cm)
    monkeypatch.setattr(sandbox_tool, "load_attachments_for_ids", _fake_load_attachments_for_ids)
    monkeypatch.setattr(sandbox_tool, "execute_sandbox", _fake_execute_sandbox)
    monkeypatch.setattr(sandbox_tool, "save_uploaded_attachments", _fake_save_uploaded_attachments)

    output = await sandbox_tool.run_python_analysis.ainvoke(
        {
            "code": "print('hello')",
            "attachment_ids_json": "[]",
        }
    )

    payload = json.loads(output)
    assert payload["status"] == "succeeded"
    assert payload["summary"].startswith("Sandbox execution completed")
    assert payload["artifact_attachment_ids"] == []
