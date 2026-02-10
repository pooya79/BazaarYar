from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from server.features.agent.sandbox import python_sandbox_tool as sandbox_tool
from server.features.agent.sandbox.sandbox_schema import (
    SandboxExecutionResult,
    SandboxInputFileMapping,
)
from server.core.config import get_settings


@asynccontextmanager
async def _fake_session_cm():
    yield object()


def test_python_sandbox_tool_exposes_attachment_ids_argument():
    args = sandbox_tool.run_python_code.args
    assert "attachment_ids" in args
    assert "attachment_ids_json" not in args
    assert sandbox_tool.run_python_code.name == "run_python_code"


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

    output = await sandbox_tool.run_python_code.ainvoke(
        {
            "code": "print('hello')",
        }
    )

    payload = json.loads(output)
    assert payload["status"] == "succeeded"
    assert payload["summary"].startswith("Sandbox execution completed")
    assert payload["artifact_attachment_ids"] == []
    assert payload["input_files"] == []


@pytest.mark.asyncio
async def test_python_sandbox_tool_accepts_attachment_ids_as_list(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_tool_enabled", True)
    monkeypatch.setattr(settings, "sandbox_max_code_chars", 20_000)

    async def _fake_load_attachments_for_ids(_session, attachment_ids, *, allow_json_fallback=True):
        _ = allow_json_fallback
        assert attachment_ids == ["att-1", "att-2"]
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

    output = await sandbox_tool.run_python_code.ainvoke(
        {
            "code": "print('hello')",
            "attachment_ids": ["att-1", "att-2"],
        }
    )

    payload = json.loads(output)
    assert payload["status"] == "succeeded"


@pytest.mark.asyncio
async def test_python_sandbox_tool_uses_request_context_attachments_and_returns_input_manifest(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_tool_enabled", True)
    monkeypatch.setattr(settings, "sandbox_max_code_chars", 20_000)

    context = SimpleNamespace(latest_user_attachment_ids=("att-ctx",))
    attachment = SimpleNamespace(
        id="att-ctx",
        filename="campaign_data.csv",
        storage_path="server/storage/uploads/files/campaign_data.csv",
        content_type="text/csv",
    )

    async def _fake_load_attachments_for_ids(_session, attachment_ids, *, allow_json_fallback=True):
        _ = allow_json_fallback
        assert attachment_ids == ["att-ctx"]
        return [attachment]

    async def _fake_execute_sandbox(request, *, on_status=None):
        if on_status is not None:
            await on_status("executing", "Running sandbox")
        assert len(request.files) == 1
        assert request.files[0].attachment_id == "att-ctx"
        return SandboxExecutionResult(
            run_id=request.run_id,
            status="succeeded",
            summary="Sandbox execution completed.",
            stdout_tail="ok",
            stderr_tail="",
            input_files=[
                SandboxInputFileMapping(
                    attachment_id="att-ctx",
                    original_filename="campaign_data.csv",
                    sandbox_filename="01_campaign_data.csv",
                    content_type="text/csv",
                    input_path="/workspace/input/01_campaign_data.csv",
                )
            ],
            artifacts=[],
        )

    async def _fake_save_uploaded_attachments(_session, uploaded_files):
        assert uploaded_files == []
        return []

    monkeypatch.setattr(sandbox_tool, "AsyncSessionLocal", _fake_session_cm)
    monkeypatch.setattr(sandbox_tool, "get_request_context", lambda: context)
    monkeypatch.setattr(sandbox_tool, "load_attachments_for_ids", _fake_load_attachments_for_ids)
    monkeypatch.setattr(sandbox_tool, "execute_sandbox", _fake_execute_sandbox)
    monkeypatch.setattr(sandbox_tool, "save_uploaded_attachments", _fake_save_uploaded_attachments)

    output = await sandbox_tool.run_python_code.ainvoke(
        {
            "code": "print('hello')",
        }
    )

    payload = json.loads(output)
    assert payload["status"] == "succeeded"
    assert payload["input_files"] == [
        {
            "attachment_id": "att-ctx",
            "original_filename": "campaign_data.csv",
            "sandbox_filename": "01_campaign_data.csv",
            "content_type": "text/csv",
            "input_path": "/workspace/input/01_campaign_data.csv",
        }
    ]
