from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from langchain.tools import tool
from sqlalchemy import select

from server.features.agent.prompts import RUN_PYTHON_CODE_TOOL_DESCRIPTION
from server.features.attachments import (
    load_attachments_for_ids,
    store_generated_artifact,
)
from server.features.agent.sandbox.event_bus import emit_sandbox_status, get_request_context
from server.features.agent.sandbox.dataframe_bootstrap import SANDBOX_DATAFRAME_BOOTSTRAP_CODE
from server.features.agent.sandbox.session_executor import execute_persistent_sandbox
from server.features.agent.sandbox.sandbox_executor import execute_sandbox
from server.features.agent.sandbox.sandbox_schema import SandboxExecutionRequest, SandboxInputFile
from server.core.config import get_settings
from server.db.models import Message, MessageAttachment
from server.db.session import AsyncSessionLocal
from server.features.chat import save_uploaded_attachments


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True)


def _normalize_str_list(raw: list[str] | None) -> list[str]:
    if raw is None:
        return []

    cleaned: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())
    return cleaned


def _failed_payload(summary: str, *, run_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "failed",
        "summary": summary,
        "artifact_attachment_ids": [],
        "artifacts": [],
        "input_files": [],
        "stdout_tail": "",
        "stderr_tail": "",
    }
    if run_id:
        payload["run_id"] = run_id
    return payload


def _compose_sandbox_code(code: str) -> str:
    return f"{SANDBOX_DATAFRAME_BOOTSTRAP_CODE}\n\n{code}"


async def _conversation_attachment_ids(session: Any, *, conversation_id: str) -> list[str]:
    if not hasattr(session, "execute"):
        return []

    try:
        conversation_uuid = UUID(conversation_id)
    except ValueError:
        return []

    stmt = (
        select(MessageAttachment.attachment_id)
        .join(Message, MessageAttachment.message_id == Message.id)
        .where(Message.conversation_id == conversation_uuid)
        .order_by(
            Message.created_at.asc(),
            Message.id.asc(),
            MessageAttachment.position.asc(),
            MessageAttachment.attachment_id.asc(),
        )
    )
    rows = (await session.execute(stmt)).scalars().all()

    output: list[str] = []
    seen: set[str] = set()
    for row in rows:
        attachment_id = str(row)
        if attachment_id in seen:
            continue
        seen.add(attachment_id)
        output.append(attachment_id)
    return output


async def _resolve_attachment_ids(session: Any, *, context: Any | None) -> list[str]:
    if context is None:
        return []

    conversation_id = getattr(context, "conversation_id", None)
    if isinstance(conversation_id, str) and conversation_id.strip():
        return await _conversation_attachment_ids(
            session,
            conversation_id=conversation_id.strip(),
        )

    latest_ids = list(getattr(context, "latest_user_attachment_ids", ()))
    return _normalize_str_list(latest_ids)


@tool(
    "run_python_code",
    description=RUN_PYTHON_CODE_TOOL_DESCRIPTION
)
async def run_python_code(
    code: str,
    description: str | None = None,
) -> str:
    settings = get_settings()
    if not settings.sandbox_tool_enabled:
        return _json(_failed_payload("Sandbox tool is disabled."))

    if len(code) > settings.sandbox_max_code_chars:
        return _json(
            _failed_payload(
                f"Code length exceeds max of {settings.sandbox_max_code_chars} characters."
            )
        )

    context = get_request_context()
    conversation_id = getattr(context, "conversation_id", None) if context is not None else None

    run_id = str(uuid4())

    async def _status_callback(stage: str, message: str) -> None:
        await emit_sandbox_status(run_id=run_id, stage=stage, message=message)

    try:
        async with AsyncSessionLocal() as session:
            attachment_ids = await _resolve_attachment_ids(session, context=context)
            attachments = await load_attachments_for_ids(
                session,
                attachment_ids,
                allow_json_fallback=False,
            )
            sandbox_code = _compose_sandbox_code(code)
            sandbox_request = SandboxExecutionRequest(
                run_id=run_id,
                code=sandbox_code,
                files=[
                    SandboxInputFile(
                        attachment_id=item.id,
                        filename=item.filename,
                        storage_path=item.storage_path,
                        content_type=item.content_type,
                    )
                    for item in attachments
                ],
            )
            if conversation_id and settings.sandbox_persist_sessions:
                result = await execute_persistent_sandbox(
                    session=session,
                    conversation_id=conversation_id,
                    request=sandbox_request,
                    on_status=_status_callback,
                )
            else:
                result = await execute_sandbox(sandbox_request, on_status=_status_callback)

            stored_artifacts = []
            for artifact in result.artifacts:
                stored_artifacts.append(
                    store_generated_artifact(
                        filename=artifact.filename,
                        payload=artifact.payload,
                        content_type=artifact.content_type,
                    )
                )

            if stored_artifacts:
                await save_uploaded_attachments(session, stored_artifacts)

            artifact_ids = [item.id for item in stored_artifacts]
            artifact_rows = [
                {
                    "id": item.id,
                    "filename": item.filename,
                    "content_type": item.content_type,
                    "media_type": item.media_type,
                    "size_bytes": item.size_bytes,
                }
                for item in stored_artifacts
            ]
            input_files = [item.model_dump(mode="json") for item in result.input_files]

            summary_suffix = f" ({description})" if description else ""
            summary = result.summary + summary_suffix
            return _json(
                {
                    "status": result.status,
                    "summary": summary,
                    "artifact_attachment_ids": artifact_ids,
                    "artifacts": artifact_rows,
                    "input_files": input_files,
                    "stdout_tail": result.stdout_tail,
                    "stderr_tail": result.stderr_tail,
                    "run_id": run_id,
                    "sandbox_session_id": result.sandbox_session_id,
                    "sandbox_reused": result.sandbox_reused,
                    "request_sequence": result.request_sequence,
                    "queue_wait_ms": result.queue_wait_ms,
                }
            )
    except Exception as exc:
        await emit_sandbox_status(run_id=run_id, stage="failed", message=str(exc))
        return _json(_failed_payload(f"Sandbox execution failed: {exc}", run_id=run_id))


PYTHON_SANDBOX_TOOLS = [run_python_code]
