from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Awaitable, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import get_settings
from server.db.models import ConversationSandboxSession
from server.features.agent.sandbox.sandbox_schema import (
    SandboxArtifact,
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxInputFileMapping,
    SandboxRunnerArtifact,
)
from server.features.attachments import resolve_storage_path

_STATUS_CALLBACK = Callable[[str, str], Awaitable[None]]
_FILENAME_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_CONTAINER_NAME_PREFIX = "bazaaryar-sandbox-session-"


class SessionResetError(RuntimeError):
    pass


@dataclass(frozen=True)
class _SessionResource:
    id: UUID
    container_name: str
    workspace_path: str


@dataclass(frozen=True)
class _EnqueueResult:
    session_id: UUID
    sandbox_reused: bool
    request_sequence: int
    workspace_dir: Path
    response_path: Path
    response_artifacts_dir: Path
    input_files: list[SandboxInputFileMapping]


@dataclass(frozen=True)
class SandboxSessionStatus:
    alive: bool
    session_id: str | None
    request_sequence: int | None
    reason: str
    last_used_at: datetime | None
    available_files: list[str]


def _sanitize_filename(value: str) -> str:
    cleaned = _FILENAME_TOKEN_RE.sub("_", value).strip("._")
    return cleaned or "input"


def _sandbox_sessions_root() -> Path:
    root = resolve_storage_path("server/storage/sandbox_sessions")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _session_workspace_path(session_id: UUID) -> Path:
    return _sandbox_sessions_root() / str(session_id)


def _container_name(session_id: UUID) -> str:
    return f"{_CONTAINER_NAME_PREFIX}{session_id}"


def _manifest_path(workspace_dir: Path) -> Path:
    return workspace_dir / "state" / "input_manifest.json"


def _runner_ready_path(workspace_dir: Path) -> Path:
    return workspace_dir / "state" / "runner.ready"


def _atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(value, encoding="utf-8")
    os.replace(tmp_path, path)


def _ensure_workspace_dirs(workspace_dir: Path) -> None:
    (workspace_dir / "state").mkdir(parents=True, exist_ok=True)
    (workspace_dir / "input").mkdir(parents=True, exist_ok=True)
    (workspace_dir / "output").mkdir(parents=True, exist_ok=True)
    (workspace_dir / "requests").mkdir(parents=True, exist_ok=True)
    (workspace_dir / "responses").mkdir(parents=True, exist_ok=True)
    (workspace_dir / "response_artifacts").mkdir(parents=True, exist_ok=True)
    workspace_dir.chmod(0o777)
    (workspace_dir / "state").chmod(0o777)
    (workspace_dir / "input").chmod(0o777)
    (workspace_dir / "output").chmod(0o777)
    (workspace_dir / "requests").chmod(0o777)
    (workspace_dir / "responses").chmod(0o777)
    (workspace_dir / "response_artifacts").chmod(0o777)


def _load_manifest(workspace_dir: Path) -> list[SandboxInputFileMapping]:
    path = _manifest_path(workspace_dir)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    output: list[SandboxInputFileMapping] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            output.append(SandboxInputFileMapping.model_validate(item))
        except Exception:
            continue
    return output


def _write_manifest(workspace_dir: Path, manifest: list[SandboxInputFileMapping]) -> None:
    payload = [item.model_dump(mode="json") for item in manifest]
    _atomic_write_text(
        _manifest_path(workspace_dir),
        json.dumps(payload, ensure_ascii=True),
    )


def _sync_input_files(
    workspace_dir: Path,
    request: SandboxExecutionRequest,
) -> list[SandboxInputFileMapping]:
    input_dir = workspace_dir / "input"
    manifest = _load_manifest(workspace_dir)
    by_attachment_id = {item.attachment_id: item for item in manifest}
    used_names = {item.sandbox_filename for item in manifest}
    next_index = len(manifest) + 1

    for item in request.files:
        source = resolve_storage_path(item.storage_path)
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Attachment '{item.attachment_id}' file does not exist.")

        existing = by_attachment_id.get(item.attachment_id)
        if existing is not None:
            target = input_dir / existing.sandbox_filename
            if not target.exists():
                shutil.copyfile(source, target)
                target.chmod(0o444)
            continue

        safe_name = _sanitize_filename(item.filename)
        while True:
            target_name = f"{next_index:02d}_{safe_name}"
            next_index += 1
            if target_name not in used_names:
                break
        used_names.add(target_name)
        target = input_dir / target_name
        shutil.copyfile(source, target)
        target.chmod(0o444)
        mapped = SandboxInputFileMapping(
            attachment_id=item.attachment_id,
            original_filename=item.filename,
            sandbox_filename=target_name,
            content_type=item.content_type,
            input_path=f"/workspace/input/{target_name}",
        )
        manifest.append(mapped)
        by_attachment_id[item.attachment_id] = mapped

    _write_manifest(workspace_dir, manifest)
    return manifest


async def _emit_status(callback: _STATUS_CALLBACK | None, stage: str, message: str) -> None:
    if callback is None:
        return
    await callback(stage, message)


async def _run_subprocess(*command: str) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return (
        process.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


async def _docker_container_exists(container_name: str) -> bool:
    settings = get_settings()
    code, _stdout, _stderr = await _run_subprocess(
        settings.sandbox_docker_bin,
        "inspect",
        container_name,
    )
    return code == 0


async def _docker_container_running(container_name: str) -> bool:
    settings = get_settings()
    code, stdout, _stderr = await _run_subprocess(
        settings.sandbox_docker_bin,
        "inspect",
        "-f",
        "{{.State.Running}}",
        container_name,
    )
    return code == 0 and stdout.strip().lower() == "true"


async def _docker_remove_container(container_name: str) -> None:
    settings = get_settings()
    await _run_subprocess(settings.sandbox_docker_bin, "rm", "-f", container_name)


def _session_docker_run_command(*, workspace_dir: Path, container_name: str) -> list[str]:
    settings = get_settings()
    return [
        settings.sandbox_docker_bin,
        "run",
        "-d",
        "--name",
        container_name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        "--memory",
        f"{settings.sandbox_max_memory_mb}m",
        "--cpus",
        str(settings.sandbox_max_cpu),
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "-v",
        f"{workspace_dir}:/workspace:rw",
        "--workdir",
        "/workspace/output",
        "--entrypoint",
        "/usr/bin/tini",
        settings.sandbox_docker_image,
        "--",
        "python",
        "/opt/sandbox/session_runner.py",
    ]


async def _ensure_session_container(*, workspace_dir: Path, container_name: str) -> None:
    settings = get_settings()
    if await _docker_container_running(container_name):
        return

    if await _docker_container_exists(container_name):
        code, _stdout, stderr = await _run_subprocess(settings.sandbox_docker_bin, "start", container_name)
        if code != 0:
            raise RuntimeError(f"Failed to start sandbox session container: {stderr.strip() or code}")
    else:
        command = _session_docker_run_command(workspace_dir=workspace_dir, container_name=container_name)
        code, _stdout, stderr = await _run_subprocess(*command)
        if code != 0:
            raise RuntimeError(f"Failed to run sandbox session container: {stderr.strip() or code}")

    ready_path = _runner_ready_path(workspace_dir)
    deadline = asyncio.get_event_loop().time() + 10.0
    poll_interval = max(settings.sandbox_session_poll_interval_ms, 10) / 1000
    while asyncio.get_event_loop().time() < deadline:
        if ready_path.exists():
            return
        await asyncio.sleep(poll_interval)

    raise RuntimeError("Sandbox session runner did not become ready in time.")


def _validate_and_load_session_artifacts(
    *,
    response_artifacts_dir: Path,
    artifacts_payload: list[dict[str, str]],
) -> list[SandboxArtifact]:
    settings = get_settings()
    if len(artifacts_payload) > settings.sandbox_max_artifacts:
        raise ValueError(
            f"Sandbox produced {len(artifacts_payload)} artifacts, exceeding limit {settings.sandbox_max_artifacts}."
        )

    artifacts: list[SandboxArtifact] = []
    base = response_artifacts_dir.resolve()
    for raw_item in artifacts_payload:
        item = SandboxRunnerArtifact.model_validate(raw_item)
        path = (response_artifacts_dir / item.rel_path).resolve()
        if base not in path.parents and path != base:
            raise ValueError(f"Artifact path '{item.rel_path}' escapes output directory.")
        if not path.exists() or not path.is_file():
            raise ValueError(f"Artifact file '{item.rel_path}' not found.")
        size = path.stat().st_size
        if size > settings.sandbox_max_artifact_bytes:
            raise ValueError(
                f"Artifact '{item.filename}' exceeds size limit of {settings.sandbox_max_artifact_bytes} bytes."
            )
        artifacts.append(
            SandboxArtifact(
                filename=item.filename,
                content_type=item.content_type,
                size_bytes=size,
                payload=path.read_bytes(),
            )
        )
    return artifacts


async def _cleanup_runtime_resource(resource: _SessionResource) -> None:
    await _docker_remove_container(resource.container_name)
    workspace_dir = resolve_storage_path(resource.workspace_path)
    shutil.rmtree(workspace_dir, ignore_errors=True)


def _manifest_available_files(workspace_dir: Path) -> list[str]:
    manifest = _load_manifest(workspace_dir)
    output: list[str] = []
    for item in manifest:
        if item.sandbox_filename:
            output.append(item.sandbox_filename)
    return output


async def get_conversation_sandbox_status(
    session: AsyncSession,
    *,
    conversation_id: str,
) -> SandboxSessionStatus:
    try:
        conversation_uuid = UUID(conversation_id)
    except ValueError:
        return SandboxSessionStatus(
            alive=False,
            session_id=None,
            request_sequence=None,
            reason="no_session",
            last_used_at=None,
            available_files=[],
        )

    if not hasattr(session, "execute"):
        return SandboxSessionStatus(
            alive=False,
            session_id=None,
            request_sequence=None,
            reason="no_session",
            last_used_at=None,
            available_files=[],
        )

    stmt = select(ConversationSandboxSession).where(
        ConversationSandboxSession.conversation_id == conversation_uuid
    )
    sandbox_session = (await session.execute(stmt)).scalar_one_or_none()
    if sandbox_session is None:
        return SandboxSessionStatus(
            alive=False,
            session_id=None,
            request_sequence=None,
            reason="no_session",
            last_used_at=None,
            available_files=[],
        )

    request_sequence = int(sandbox_session.next_request_seq) - 1
    if request_sequence <= 0:
        request_sequence = None

    settings = get_settings()
    ttl_seconds = max(0, settings.sandbox_session_idle_ttl_seconds)
    last_used_at = sandbox_session.last_used_at
    if ttl_seconds > 0 and last_used_at < datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds):
        return SandboxSessionStatus(
            alive=False,
            session_id=str(sandbox_session.id),
            request_sequence=request_sequence,
            reason="ttl_expired",
            last_used_at=last_used_at,
            available_files=[],
        )

    workspace_dir = resolve_storage_path(sandbox_session.workspace_path)
    if not workspace_dir.exists() or not workspace_dir.is_dir():
        return SandboxSessionStatus(
            alive=False,
            session_id=str(sandbox_session.id),
            request_sequence=request_sequence,
            reason="workspace_missing",
            last_used_at=last_used_at,
            available_files=[],
        )

    if not await _docker_container_running(sandbox_session.container_name):
        return SandboxSessionStatus(
            alive=False,
            session_id=str(sandbox_session.id),
            request_sequence=request_sequence,
            reason="container_not_running",
            last_used_at=last_used_at,
            available_files=[],
        )

    return SandboxSessionStatus(
        alive=True,
        session_id=str(sandbox_session.id),
        request_sequence=request_sequence,
        reason="alive",
        last_used_at=last_used_at,
        available_files=_manifest_available_files(workspace_dir),
    )


async def cleanup_stale_sandbox_sessions(session: AsyncSession) -> None:
    settings = get_settings()
    ttl_seconds = max(0, settings.sandbox_session_idle_ttl_seconds)
    now = datetime.now(timezone.utc)
    resources_to_cleanup: list[_SessionResource] = []

    if ttl_seconds > 0:
        cutoff = now - timedelta(seconds=ttl_seconds)
        stale_stmt = select(ConversationSandboxSession).where(ConversationSandboxSession.last_used_at < cutoff)
        stale_rows = list((await session.execute(stale_stmt)).scalars().all())
        for row in stale_rows:
            resources_to_cleanup.append(
                _SessionResource(
                    id=row.id,
                    container_name=row.container_name,
                    workspace_path=row.workspace_path,
                )
            )
            await session.delete(row)
        if stale_rows:
            await session.commit()

    for resource in resources_to_cleanup:
        await _cleanup_runtime_resource(resource)

    known_workspace_paths = {
        resolve_storage_path(path)
        for path in (
            await session.execute(select(ConversationSandboxSession.workspace_path))
        ).scalars()
    }
    known_container_names = {
        str(name)
        for name in (
            await session.execute(select(ConversationSandboxSession.container_name))
        ).scalars()
    }
    root = _sandbox_sessions_root()
    if root.exists():
        for child in root.iterdir():
            if not child.is_dir():
                continue
            if child in known_workspace_paths:
                continue
            shutil.rmtree(child, ignore_errors=True)

    settings = get_settings()
    code, stdout, _stderr = await _run_subprocess(
        settings.sandbox_docker_bin,
        "ps",
        "-a",
        "--filter",
        f"name={_CONTAINER_NAME_PREFIX}",
        "--format",
        "{{.Names}}",
    )
    if code == 0:
        for name in [item.strip() for item in stdout.splitlines() if item.strip()]:
            if name in known_container_names:
                continue
            await _docker_remove_container(name)


async def _delete_session_row_for_conversation(
    session: AsyncSession,
    conversation_uuid: UUID,
) -> _SessionResource | None:
    stmt = (
        select(ConversationSandboxSession)
        .where(ConversationSandboxSession.conversation_id == conversation_uuid)
        .with_for_update()
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    resource = _SessionResource(
        id=row.id,
        container_name=row.container_name,
        workspace_path=row.workspace_path,
    )
    await session.delete(row)
    await session.commit()
    return resource


async def reset_conversation_sandbox(
    session: AsyncSession,
    *,
    conversation_id: str,
) -> bool:
    try:
        conversation_uuid = UUID(conversation_id)
    except ValueError:
        return False

    resource = await _delete_session_row_for_conversation(session, conversation_uuid)
    if resource is None:
        return False
    await _cleanup_runtime_resource(resource)
    return True


async def _enqueue_request(
    *,
    session: AsyncSession,
    conversation_id: str,
    request: SandboxExecutionRequest,
) -> _EnqueueResult:
    host_name = socket.gethostname()
    conversation_uuid = UUID(conversation_id)

    while True:
        reused = True
        stmt = (
            select(ConversationSandboxSession)
            .where(ConversationSandboxSession.conversation_id == conversation_uuid)
            .with_for_update()
        )
        sandbox_session = (await session.execute(stmt)).scalar_one_or_none()
        if sandbox_session is None:
            reused = False
            sandbox_id = uuid.uuid4()
            workspace_path = str(_session_workspace_path(sandbox_id))
            sandbox_session = ConversationSandboxSession(
                id=sandbox_id,
                conversation_id=conversation_uuid,
                container_name=_container_name(sandbox_id),
                workspace_path=workspace_path,
                owner_host=host_name,
            )
            session.add(sandbox_session)
            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                continue
        elif sandbox_session.owner_host != host_name:
            stale_resource = _SessionResource(
                id=sandbox_session.id,
                container_name=sandbox_session.container_name,
                workspace_path=sandbox_session.workspace_path,
            )
            await session.delete(sandbox_session)
            await session.commit()
            await _cleanup_runtime_resource(stale_resource)
            continue

        workspace_dir = resolve_storage_path(sandbox_session.workspace_path)
        _ensure_workspace_dirs(workspace_dir)
        await _ensure_session_container(
            workspace_dir=workspace_dir,
            container_name=sandbox_session.container_name,
        )

        manifest = _sync_input_files(workspace_dir, request)
        sequence = int(sandbox_session.next_request_seq)
        sandbox_session.next_request_seq = sequence + 1
        sandbox_session.last_used_at = datetime.now(timezone.utc)

        request_id = request.run_id
        request_payload = {
            "request_id": request_id,
            "code": request.code,
        }
        request_filename = f"{sequence:020d}_{request_id}.json"
        request_path = workspace_dir / "requests" / request_filename
        _atomic_write_text(request_path, json.dumps(request_payload, ensure_ascii=True))

        response_path = workspace_dir / "responses" / f"{request_id}.json"
        if response_path.exists():
            response_path.unlink(missing_ok=True)

        response_artifacts_dir = workspace_dir / "response_artifacts" / request_id
        if response_artifacts_dir.exists():
            shutil.rmtree(response_artifacts_dir, ignore_errors=True)

        await session.commit()

        return _EnqueueResult(
            session_id=sandbox_session.id,
            sandbox_reused=reused,
            request_sequence=sequence,
            workspace_dir=workspace_dir,
            response_path=response_path,
            response_artifacts_dir=response_artifacts_dir,
            input_files=manifest,
        )


async def execute_persistent_sandbox(
    *,
    session: AsyncSession,
    conversation_id: str,
    request: SandboxExecutionRequest,
    on_status: _STATUS_CALLBACK | None = None,
) -> SandboxExecutionResult:
    settings = get_settings()
    await cleanup_stale_sandbox_sessions(session)
    await _emit_status(on_status, "queueing", "Queueing request in conversation sandbox session.")

    enqueue_result = await _enqueue_request(
        session=session,
        conversation_id=conversation_id,
        request=request,
    )

    await _emit_status(on_status, "queued", "Waiting for queued sandbox request to complete.")
    wait_started = asyncio.get_event_loop().time()
    timeout_seconds = max(
        settings.sandbox_session_queue_wait_timeout_seconds,
        settings.sandbox_max_runtime_seconds,
    )
    poll_interval = max(settings.sandbox_session_poll_interval_ms, 10) / 1000
    deadline = wait_started + timeout_seconds

    response_payload: dict[str, object] | None = None
    while asyncio.get_event_loop().time() < deadline:
        if enqueue_result.response_path.exists():
            try:
                raw = enqueue_result.response_path.read_text(encoding="utf-8")
                response_payload = json.loads(raw)
            finally:
                enqueue_result.response_path.unlink(missing_ok=True)
            break
        if not enqueue_result.workspace_dir.exists():
            return SandboxExecutionResult(
                run_id=request.run_id,
                status="failed",
                summary="Sandbox session reset due previous timeout.",
                stderr_tail="",
                input_files=enqueue_result.input_files,
                error_message="Sandbox session reset due previous timeout.",
                sandbox_session_id=str(enqueue_result.session_id),
                sandbox_reused=enqueue_result.sandbox_reused,
                request_sequence=enqueue_result.request_sequence,
            )
        await asyncio.sleep(poll_interval)

    queue_wait_ms = int((asyncio.get_event_loop().time() - wait_started) * 1000)
    if response_payload is None:
        await _emit_status(on_status, "failed", "Sandbox execution timed out.")
        await reset_conversation_sandbox(session, conversation_id=conversation_id)
        return SandboxExecutionResult(
            run_id=request.run_id,
            status="timeout",
            summary="Sandbox execution timed out.",
            stderr_tail="",
            input_files=enqueue_result.input_files,
            error_message="Sandbox execution timed out.",
            sandbox_session_id=str(enqueue_result.session_id),
            sandbox_reused=enqueue_result.sandbox_reused,
            request_sequence=enqueue_result.request_sequence,
            queue_wait_ms=queue_wait_ms,
        )

    artifacts_payload = response_payload.get("artifacts")
    if not isinstance(artifacts_payload, list):
        artifacts_payload = []

    try:
        artifacts = _validate_and_load_session_artifacts(
            response_artifacts_dir=enqueue_result.response_artifacts_dir,
            artifacts_payload=[item for item in artifacts_payload if isinstance(item, dict)],
        )
    except Exception as exc:
        return SandboxExecutionResult(
            run_id=request.run_id,
            status="failed",
            summary=str(exc),
            stderr_tail=str(response_payload.get("stderr_tail") or ""),
            input_files=enqueue_result.input_files,
            error_message=str(exc),
            sandbox_session_id=str(enqueue_result.session_id),
            sandbox_reused=enqueue_result.sandbox_reused,
            request_sequence=enqueue_result.request_sequence,
            queue_wait_ms=queue_wait_ms,
        )
    finally:
        if enqueue_result.response_artifacts_dir.exists():
            shutil.rmtree(enqueue_result.response_artifacts_dir, ignore_errors=True)

    status = str(response_payload.get("status") or "failed")
    if status not in {"succeeded", "failed", "timeout"}:
        status = "failed"
    summary = str(response_payload.get("summary") or "Sandbox execution failed.")
    stdout_tail = str(response_payload.get("stdout_tail") or "")
    stderr_tail = str(response_payload.get("stderr_tail") or "")
    error_message_raw = response_payload.get("error_message")
    error_message = str(error_message_raw) if error_message_raw else None

    await _emit_status(
        on_status,
        "completed" if status == "succeeded" else "failed",
        summary,
    )
    return SandboxExecutionResult(
        run_id=request.run_id,
        status=status,
        summary=summary,
        stdout_tail=stdout_tail,
        stderr_tail=stderr_tail,
        input_files=enqueue_result.input_files,
        artifacts=artifacts,
        error_message=error_message,
        sandbox_session_id=str(enqueue_result.session_id),
        sandbox_reused=enqueue_result.sandbox_reused,
        request_sequence=enqueue_result.request_sequence,
        queue_wait_ms=queue_wait_ms,
    )
