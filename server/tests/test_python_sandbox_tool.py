from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from server.features.agent.sandbox import python_sandbox_tool as sandbox_tool
from server.features.agent.sandbox.dataframe_bootstrap import (
    SANDBOX_DATAFRAME_BOOTSTRAP_MARKER,
)
from server.features.agent.sandbox.sandbox_schema import (
    SandboxExecutionResult,
    SandboxInputFileMapping,
)
from server.core.config import get_settings


@asynccontextmanager
async def _fake_session_cm():
    yield object()


def _assert_bootstrap_prepended(composed_code: str, user_code: str) -> None:
    assert SANDBOX_DATAFRAME_BOOTSTRAP_MARKER in composed_code
    assert composed_code.endswith(user_code)
    assert composed_code.index(SANDBOX_DATAFRAME_BOOTSTRAP_MARKER) < composed_code.index(user_code)


def test_python_sandbox_tool_exposes_no_file_selector_args():
    args = sandbox_tool.run_python_code.args
    assert "input_filenames" not in args
    assert "attachment_ids" not in args
    assert "attachment_ids_json" not in args
    assert sandbox_tool.run_python_code.name == "run_python_code"
    assert "input_filenames" not in sandbox_tool.run_python_code.description
    assert "attachment_ids" not in sandbox_tool.run_python_code.description
    assert "load_dataframe(path, **kwargs)" in sandbox_tool.run_python_code.description


def test_compose_sandbox_code_prepends_dataframe_bootstrap():
    user_code = "print('hello')"
    composed = sandbox_tool._compose_sandbox_code(user_code)
    _assert_bootstrap_prepended(composed, user_code)


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
        _assert_bootstrap_prepended(request.code, "print('hello')")
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
async def test_python_sandbox_tool_mounts_all_conversation_attachments(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_tool_enabled", True)
    monkeypatch.setattr(settings, "sandbox_max_code_chars", 20_000)
    monkeypatch.setattr(settings, "sandbox_persist_sessions", False)

    context = SimpleNamespace(
        latest_user_attachment_ids=("att-latest-only",),
        conversation_id="5e07ec16-b499-4c34-98c3-044f2a955c12",
    )
    attachments = [
        SimpleNamespace(
            id="att-1",
            filename="a.csv",
            storage_path="server/storage/uploads/files/a.csv",
            content_type="text/csv",
        ),
        SimpleNamespace(
            id="att-2",
            filename="b.csv",
            storage_path="server/storage/uploads/files/b.csv",
            content_type="text/csv",
        ),
        SimpleNamespace(
            id="att-3",
            filename="c.csv",
            storage_path="server/storage/uploads/files/c.csv",
            content_type="text/csv",
        ),
    ]

    async def _fake_load_attachments_for_ids(_session, attachment_ids, *, allow_json_fallback=True):
        _ = allow_json_fallback
        assert attachment_ids == ["att-1", "att-2", "att-3"]
        return attachments

    async def _fake_execute_sandbox(request, *, on_status=None):
        if on_status is not None:
            await on_status("executing", "Running sandbox")
        assert [item.attachment_id for item in request.files] == ["att-1", "att-2", "att-3"]
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
    monkeypatch.setattr(sandbox_tool, "get_request_context", lambda: context)
    async def _fake_conversation_attachment_ids(_session, *, conversation_id):
        if conversation_id == "5e07ec16-b499-4c34-98c3-044f2a955c12":
            return ["att-1", "att-2", "att-3"]
        return []

    monkeypatch.setattr(
        sandbox_tool,
        "_conversation_attachment_ids",
        _fake_conversation_attachment_ids,
    )
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


@pytest.mark.asyncio
async def test_python_sandbox_tool_uses_only_conversation_attachments_when_conversation_has_none(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_tool_enabled", True)
    monkeypatch.setattr(settings, "sandbox_max_code_chars", 20_000)
    monkeypatch.setattr(settings, "sandbox_persist_sessions", False)

    context = SimpleNamespace(
        latest_user_attachment_ids=("att-ctx",),
        conversation_id="5e07ec16-b499-4c34-98c3-044f2a955c12",
    )
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
    monkeypatch.setattr(sandbox_tool, "get_request_context", lambda: context)
    async def _fake_conversation_attachment_ids(_session, *, conversation_id):
        _ = conversation_id
        return []

    monkeypatch.setattr(
        sandbox_tool,
        "_conversation_attachment_ids",
        _fake_conversation_attachment_ids,
    )
    monkeypatch.setattr(sandbox_tool, "load_attachments_for_ids", _fake_load_attachments_for_ids)
    monkeypatch.setattr(sandbox_tool, "execute_sandbox", _fake_execute_sandbox)
    monkeypatch.setattr(sandbox_tool, "save_uploaded_attachments", _fake_save_uploaded_attachments)

    output = await sandbox_tool.run_python_code.ainvoke({"code": "print('hello')"})

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


@pytest.mark.asyncio
async def test_python_sandbox_tool_uses_persistent_session_when_conversation_context_is_present(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_tool_enabled", True)
    monkeypatch.setattr(settings, "sandbox_persist_sessions", True)
    monkeypatch.setattr(settings, "sandbox_max_code_chars", 20_000)

    context = SimpleNamespace(
        latest_user_attachment_ids=(),
        conversation_id="conv-1",
    )

    async def _fake_load_attachments_for_ids(_session, attachment_ids, *, allow_json_fallback=True):
        _ = (attachment_ids, allow_json_fallback)
        return []

    async def _fake_execute_persistent_sandbox(*, session, conversation_id, request, on_status=None):
        _ = session
        assert conversation_id == "conv-1"
        assert request.files == []
        _assert_bootstrap_prepended(request.code, "print('hello')")
        if on_status is not None:
            await on_status("executing", "Running sandbox")
        return SandboxExecutionResult(
            run_id=request.run_id,
            status="succeeded",
            summary="Sandbox execution completed.",
            stdout_tail="ok",
            stderr_tail="",
            artifacts=[],
            sandbox_session_id="session-1",
            sandbox_reused=True,
            request_sequence=2,
            queue_wait_ms=11,
        )

    async def _fake_save_uploaded_attachments(_session, uploaded_files):
        assert uploaded_files == []
        return []

    async def _unexpected_execute_sandbox(*_args, **_kwargs):
        raise AssertionError("execute_sandbox should not be used when conversation_id is present.")

    monkeypatch.setattr(sandbox_tool, "AsyncSessionLocal", _fake_session_cm)
    monkeypatch.setattr(sandbox_tool, "get_request_context", lambda: context)
    monkeypatch.setattr(sandbox_tool, "load_attachments_for_ids", _fake_load_attachments_for_ids)
    monkeypatch.setattr(sandbox_tool, "execute_persistent_sandbox", _fake_execute_persistent_sandbox)
    monkeypatch.setattr(sandbox_tool, "execute_sandbox", _unexpected_execute_sandbox)
    monkeypatch.setattr(sandbox_tool, "save_uploaded_attachments", _fake_save_uploaded_attachments)

    output = await sandbox_tool.run_python_code.ainvoke({"code": "print('hello')"})

    payload = json.loads(output)
    assert payload["status"] == "succeeded"
    assert payload["sandbox_session_id"] == "session-1"
    assert payload["sandbox_reused"] is True
    assert payload["request_sequence"] == 2
    assert payload["queue_wait_ms"] == 11
