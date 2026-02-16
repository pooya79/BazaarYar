from __future__ import annotations

import asyncio
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from server.core.config import get_settings
from server.features.agent.sandbox import session_executor
from server.features.agent.sandbox.sandbox_schema import SandboxExecutionRequest, SandboxInputFile


class _ScalarOneOrNoneResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _StatusSession:
    def __init__(self, row):
        self._row = row

    async def execute(self, _stmt):
        return _ScalarOneOrNoneResult(self._row)


def _build_enqueue_result(tmp_path: Path):
    workspace_dir = tmp_path / str(uuid4())
    workspace_dir.mkdir(parents=True, exist_ok=True)
    response_path = workspace_dir / "responses" / "req-1.json"
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_artifacts_dir = workspace_dir / "response_artifacts" / "req-1"
    response_artifacts_dir.mkdir(parents=True, exist_ok=True)
    return session_executor._EnqueueResult(
        session_id=uuid4(),
        sandbox_reused=True,
        request_sequence=1,
        workspace_dir=workspace_dir,
        response_path=response_path,
        response_artifacts_dir=response_artifacts_dir,
        input_files=[],
    )


@pytest.mark.asyncio
async def test_execute_persistent_sandbox_timeout_resets_session(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_session_queue_wait_timeout_seconds", 0)
    monkeypatch.setattr(settings, "sandbox_max_runtime_seconds", 0)
    monkeypatch.setattr(settings, "sandbox_session_poll_interval_ms", 10)

    enqueue_result = _build_enqueue_result(tmp_path)

    async def _fake_cleanup(_session):
        return None

    async def _fake_enqueue(*, session, conversation_id, request):
        _ = (session, conversation_id, request)
        return enqueue_result

    reset_calls: list[str] = []

    async def _fake_reset(_session, *, conversation_id: str):
        reset_calls.append(conversation_id)
        return True

    monkeypatch.setattr(session_executor, "cleanup_stale_sandbox_sessions", _fake_cleanup)
    monkeypatch.setattr(session_executor, "_enqueue_request", _fake_enqueue)
    monkeypatch.setattr(session_executor, "reset_conversation_sandbox", _fake_reset)

    result = await session_executor.execute_persistent_sandbox(
        session=object(),
        conversation_id=str(uuid4()),
        request=SandboxExecutionRequest(run_id="req-1", code="print('x')", files=[]),
    )

    assert result.status == "timeout"
    assert reset_calls


@pytest.mark.asyncio
async def test_execute_persistent_sandbox_fails_waiters_when_workspace_is_reset(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_session_queue_wait_timeout_seconds", 1)
    monkeypatch.setattr(settings, "sandbox_max_runtime_seconds", 1)
    monkeypatch.setattr(settings, "sandbox_session_poll_interval_ms", 10)

    enqueue_result = _build_enqueue_result(tmp_path)

    async def _fake_cleanup(_session):
        return None

    async def _fake_enqueue(*, session, conversation_id, request):
        _ = (session, conversation_id, request)
        return enqueue_result

    async def _delete_workspace():
        await asyncio.sleep(0.05)
        shutil.rmtree(enqueue_result.workspace_dir, ignore_errors=True)

    monkeypatch.setattr(session_executor, "cleanup_stale_sandbox_sessions", _fake_cleanup)
    monkeypatch.setattr(session_executor, "_enqueue_request", _fake_enqueue)

    delete_task = asyncio.create_task(_delete_workspace())
    result = await session_executor.execute_persistent_sandbox(
        session=object(),
        conversation_id=str(uuid4()),
        request=SandboxExecutionRequest(run_id="req-1", code="print('x')", files=[]),
    )
    await delete_task

    assert result.status == "failed"
    assert "session reset due previous timeout" in result.summary.lower()


@pytest.mark.asyncio
async def test_execute_persistent_sandbox_returns_response_artifacts(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_session_queue_wait_timeout_seconds", 1)
    monkeypatch.setattr(settings, "sandbox_max_runtime_seconds", 1)
    monkeypatch.setattr(settings, "sandbox_session_poll_interval_ms", 10)

    enqueue_result = _build_enqueue_result(tmp_path)
    artifact_file = enqueue_result.response_artifacts_dir / "plot.png"
    artifact_file.write_bytes(b"PNG")
    enqueue_result.response_path.write_text(
        json.dumps(
            {
                "request_id": "req-1",
                "status": "succeeded",
                "summary": "Sandbox execution completed.",
                "stdout_tail": "ok",
                "stderr_tail": "",
                "artifacts": [
                    {
                        "filename": "plot.png",
                        "rel_path": "plot.png",
                        "content_type": "image/png",
                    }
                ],
                "error_message": None,
            }
        ),
        encoding="utf-8",
    )

    async def _fake_cleanup(_session):
        return None

    async def _fake_enqueue(*, session, conversation_id, request):
        _ = (session, conversation_id, request)
        return enqueue_result

    monkeypatch.setattr(session_executor, "cleanup_stale_sandbox_sessions", _fake_cleanup)
    monkeypatch.setattr(session_executor, "_enqueue_request", _fake_enqueue)

    result = await session_executor.execute_persistent_sandbox(
        session=object(),
        conversation_id=str(uuid4()),
        request=SandboxExecutionRequest(run_id="req-1", code="print('x')", files=[]),
    )

    assert result.status == "succeeded"
    assert result.artifacts and result.artifacts[0].filename == "plot.png"


@pytest.mark.asyncio
async def test_get_conversation_sandbox_status_returns_ttl_expired(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_session_idle_ttl_seconds", 1)

    row = SimpleNamespace(
        id=uuid4(),
        container_name="cont-1",
        workspace_path=str(tmp_path / "workspace"),
        last_used_at=datetime.now(timezone.utc) - timedelta(seconds=5),
        next_request_seq=2,
    )
    status = await session_executor.get_conversation_sandbox_status(
        _StatusSession(row),
        conversation_id=str(uuid4()),
    )

    assert status.alive is False
    assert status.reason == "ttl_expired"
    assert status.request_sequence == 1


@pytest.mark.asyncio
async def test_get_conversation_sandbox_status_returns_container_not_running(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_session_idle_ttl_seconds", 60)

    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    row = SimpleNamespace(
        id=uuid4(),
        container_name="cont-1",
        workspace_path=str(workspace),
        last_used_at=datetime.now(timezone.utc),
        next_request_seq=1,
    )

    async def _fake_running(_name):
        return False

    monkeypatch.setattr(session_executor, "_docker_container_running", _fake_running)

    status = await session_executor.get_conversation_sandbox_status(
        _StatusSession(row),
        conversation_id=str(uuid4()),
    )

    assert status.alive is False
    assert status.reason == "container_not_running"


@pytest.mark.asyncio
async def test_get_conversation_sandbox_status_returns_alive_and_available_files(monkeypatch, tmp_path: Path):
    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_session_idle_ttl_seconds", 60)

    workspace = tmp_path / "workspace"
    (workspace / "state").mkdir(parents=True, exist_ok=True)
    (workspace / "state" / "input_manifest.json").write_text(
        json.dumps(
            [
                {
                    "attachment_id": "att-1",
                    "original_filename": "campaign.csv",
                    "sandbox_filename": "campaign data.csv",
                    "content_type": "text/csv",
                    "input_path": "/workspace/input/campaign data.csv",
                }
            ]
        ),
        encoding="utf-8",
    )
    row = SimpleNamespace(
        id=uuid4(),
        container_name="cont-1",
        workspace_path=str(workspace),
        last_used_at=datetime.now(timezone.utc),
        next_request_seq=4,
    )

    async def _fake_running(_name):
        return True

    monkeypatch.setattr(session_executor, "_docker_container_running", _fake_running)

    status = await session_executor.get_conversation_sandbox_status(
        _StatusSession(row),
        conversation_id=str(uuid4()),
    )

    assert status.alive is True
    assert status.reason == "alive"
    assert status.request_sequence == 3
    assert status.available_files == ["campaign data.csv"]


def test_sync_input_files_preserves_spaces_and_reuses_existing_mapping(tmp_path: Path):
    workspace_dir = tmp_path / "workspace"
    session_executor._ensure_workspace_dirs(workspace_dir)

    source_file = tmp_path / "campaign.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    request = SandboxExecutionRequest(
        run_id="run-1",
        code="print('ok')",
        files=[
            SandboxInputFile(
                attachment_id="att-1",
                filename="campaign data.csv",
                storage_path=str(source_file),
                content_type="text/csv",
            )
        ],
    )
    manifest = session_executor._sync_input_files(workspace_dir, request)
    assert manifest[0].sandbox_filename == "campaign data.csv"
    assert manifest[0].input_path == "/workspace/input/campaign data.csv"

    source_file.write_text("a,b\n3,4\n", encoding="utf-8")
    manifest_after = session_executor._sync_input_files(workspace_dir, request)
    assert len(manifest_after) == 1
    assert manifest_after[0].sandbox_filename == "campaign data.csv"


def test_sync_input_files_uses_prefixed_fallback_on_duplicate_filename(tmp_path: Path):
    workspace_dir = tmp_path / "workspace"
    session_executor._ensure_workspace_dirs(workspace_dir)

    source_file = tmp_path / "campaign.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    first_request = SandboxExecutionRequest(
        run_id="run-1",
        code="print('ok')",
        files=[
            SandboxInputFile(
                attachment_id="att-1",
                filename="campaign.csv",
                storage_path=str(source_file),
                content_type="text/csv",
            )
        ],
    )
    first_manifest = session_executor._sync_input_files(workspace_dir, first_request)
    assert first_manifest[0].sandbox_filename == "campaign.csv"

    duplicate_request = SandboxExecutionRequest(
        run_id="run-2",
        code="print('ok')",
        files=[
            SandboxInputFile(
                attachment_id="att-2",
                filename="campaign.csv",
                storage_path=str(source_file),
                content_type="text/csv",
            )
        ],
    )
    second_manifest = session_executor._sync_input_files(workspace_dir, duplicate_request)
    assert [item.sandbox_filename for item in second_manifest] == [
        "campaign.csv",
        "01_campaign.csv",
    ]


def test_sync_input_files_increments_prefix_when_fallback_already_taken(tmp_path: Path):
    workspace_dir = tmp_path / "workspace"
    session_executor._ensure_workspace_dirs(workspace_dir)

    source_file = tmp_path / "campaign.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    seed_request = SandboxExecutionRequest(
        run_id="run-1",
        code="print('ok')",
        files=[
            SandboxInputFile(
                attachment_id="att-1",
                filename="campaign.csv",
                storage_path=str(source_file),
                content_type="text/csv",
            ),
            SandboxInputFile(
                attachment_id="att-2",
                filename="01_campaign.csv",
                storage_path=str(source_file),
                content_type="text/csv",
            ),
        ],
    )
    seeded_manifest = session_executor._sync_input_files(workspace_dir, seed_request)
    assert [item.sandbox_filename for item in seeded_manifest] == [
        "campaign.csv",
        "01_campaign.csv",
    ]

    duplicate_request = SandboxExecutionRequest(
        run_id="run-2",
        code="print('ok')",
        files=[
            SandboxInputFile(
                attachment_id="att-3",
                filename="campaign.csv",
                storage_path=str(source_file),
                content_type="text/csv",
            )
        ],
    )
    final_manifest = session_executor._sync_input_files(workspace_dir, duplicate_request)
    assert [item.sandbox_filename for item in final_manifest] == [
        "campaign.csv",
        "01_campaign.csv",
        "02_campaign.csv",
    ]
