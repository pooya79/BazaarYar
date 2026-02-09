from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.agents.attachments import (
    StoredAttachment,
    build_attachment_message_parts_async,
    build_attachment_message_parts_for_items,
    from_db_attachment,
    load_attachments_for_ids,
    resolve_storage_path,
    store_uploaded_file,
)
from server.agents.event_bus import AgentRequestContext, bind_event_sink, bind_request_context
from server.agents.openailike_agent import extract_trace, get_agent, split_ai_content
from server.agents.streaming_schema import (
    FinalEvent,
    ReasoningDeltaEvent,
    SandboxStatusEvent,
    TextDeltaEvent,
    ToolCallDeltaEvent,
    ToolCallEvent,
    ToolResultArtifact,
    ToolResultEvent,
    encode_sse,
    stream_event_schema,
)
from server.agents.usage import extract_usage
from server.api.common import parse_uuid
from server.core.config import get_settings
from server.db.models import Attachment, Conversation, Message
from server.db.session import get_db_session
from server.domain.chat_store import (
    AttachmentNotFoundError,
    ConversationNotFoundError,
    build_context_window_for_model,
    create_conversation,
    estimate_tokens,
    save_assistant_message,
    save_assistant_message_with_attachments,
    save_uploaded_attachments,
    save_user_message_with_attachments,
)

router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str = Field(min_length=1)


class AgentRequest(BaseModel):
    message: str | None = None
    history: list[ChatMessage] | None = None
    attachment_ids: list[str] | None = None
    conversation_id: str | None = None


class AgentResponse(BaseModel):
    output_text: str
    reasoning: list[str]
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    usage: dict[str, Any] | None
    response_metadata: dict[str, Any] | None
    model: str


class UploadedAttachment(BaseModel):
    id: str
    filename: str
    content_type: str
    media_type: Literal["image", "pdf", "text", "spreadsheet", "binary"]
    size_bytes: int
    preview_text: str | None
    extraction_note: str | None


class UploadAttachmentsResponse(BaseModel):
    files: list[UploadedAttachment]


def _conversation_title_from_message(message: str | None) -> str | None:
    if not message:
        return None
    normalized = " ".join(message.split())
    if not normalized:
        return None
    return normalized[:80]


def _format_meta_block(label: str, payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return f"{label}\n{payload}"
    try:
        import json

        return f"{label}\n{json.dumps(payload, ensure_ascii=True, indent=2)}"
    except Exception:
        return f"{label}\n{payload}"


def _format_tool_call(event: dict[str, Any]) -> str:
    lines = [f"name: {event.get('name') or 'unknown'}"]
    if event.get("type"):
        lines.append(f"call_type: {event['type']}")
    if event.get("id"):
        lines.append(f"id: {event['id']}")
    args = event.get("args")
    if args:
        import json

        lines.append("args:")
        lines.append(json.dumps(args, ensure_ascii=True, indent=2))
    return "\n".join(lines)


def _parse_tool_result_payload(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def _artifact_attachment_ids(payload: dict[str, Any] | None) -> list[str]:
    if payload is None:
        return []
    raw = payload.get("artifact_attachment_ids")
    if not isinstance(raw, list):
        return []
    output: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            output.append(item.strip())
    return output


async def _tool_result_artifacts(
    session: AsyncSession,
    *,
    attachment_ids: list[str],
) -> list[ToolResultArtifact]:
    if not attachment_ids:
        return []

    loaded: list[StoredAttachment] = []
    if hasattr(session, "execute"):
        try:
            loaded = await load_attachments_for_ids(
                session,
                attachment_ids,
                allow_json_fallback=False,
            )
        except HTTPException:
            return []
    else:  # Test doubles may only implement session.get().
        for attachment_id in attachment_ids:
            try:
                file_uuid = parse_uuid(attachment_id, field_name="attachment_id")
            except HTTPException:
                continue
            row = await session.get(Attachment, file_uuid)
            if row is None:
                continue
            loaded.append(
                StoredAttachment(
                    id=str(row.id),
                    filename=row.filename,
                    content_type=row.content_type,
                    media_type=row.media_type,
                    size_bytes=row.size_bytes,
                    storage_path=row.storage_path,
                    preview_text=row.preview_text,
                    extraction_note=row.extraction_note,
                    created_at=row.created_at,
                )
            )

    return [
        ToolResultArtifact(
            id=item.id,
            filename=item.filename,
            content_type=item.content_type,
            media_type=item.media_type,
            size_bytes=item.size_bytes,
            preview_text=item.preview_text,
            extraction_note=item.extraction_note,
            download_url=f"/api/agent/attachments/{item.id}/content",
        )
        for item in loaded
    ]


def _format_tool_result(message: ToolMessage, *, payload: dict[str, Any] | None = None) -> str:
    lines: list[str] = []
    if message.tool_call_id:
        lines.append(f"tool_call_id: {message.tool_call_id}")
    if payload is None:
        lines.append(str(message.content))
        return "\n".join(lines)

    status = payload.get("status")
    summary = payload.get("summary")
    stdout_tail = payload.get("stdout_tail")
    stderr_tail = payload.get("stderr_tail")
    if status:
        lines.append(f"status: {status}")
    if summary:
        lines.append(f"summary: {summary}")
    if stdout_tail:
        lines.append("stdout:")
        lines.append(str(stdout_tail))
    if stderr_tail:
        lines.append("stderr:")
        lines.append(str(stderr_tail))
    if not lines:
        lines.append(str(message.content))
    return "\n".join(lines)


def _message_attachments(message: Message) -> list[StoredAttachment]:
    attachments: list[StoredAttachment] = []
    for link in message.attachment_links:
        if link.attachment is None:
            continue
        attachments.append(from_db_attachment(link.attachment))
    return attachments


def _to_langchain_message(message: Message) -> HumanMessage | AIMessage:
    if message.role == "assistant":
        return AIMessage(content=message.content)

    attachments = _message_attachments(message)
    if not attachments:
        return HumanMessage(content=message.content)

    attachment_context, attachment_blocks = build_attachment_message_parts_for_items(attachments)
    content: list[dict[str, Any]] = []
    if message.content.strip():
        content.append({"type": "text", "text": message.content})
    if attachment_context:
        content.append(
            {
                "type": "text",
                "text": (
                    "Attached file context:\n"
                    f"{attachment_context}\n\n"
                    "Use extracted content when relevant and call out uncertainty if extraction is incomplete."
                ),
            }
        )
    content.extend(attachment_blocks)
    if not content:
        return HumanMessage(content=message.content)
    return HumanMessage(content=content)


async def _build_messages(payload: AgentRequest, session: AsyncSession) -> list[Any]:
    messages: list[Any] = []
    if payload.history:
        for item in payload.history:
            if item.role == "assistant":
                messages.append(AIMessage(content=item.content))
            else:
                messages.append(HumanMessage(content=item.content))

    user_message = (payload.message or "").strip()
    attachment_ids = [item.strip() for item in (payload.attachment_ids or []) if item.strip()]
    attachment_context = ""
    attachment_blocks: list[dict[str, Any]] = []
    if attachment_ids:
        attachment_context, attachment_blocks = await build_attachment_message_parts_async(
            session,
            attachment_ids,
            allow_json_fallback=True,
        )

    if user_message or attachment_context or attachment_blocks:
        if attachment_blocks:
            content: list[dict[str, Any]] = []
            if user_message:
                content.append({"type": "text", "text": user_message})
            if attachment_context:
                content.append(
                    {
                        "type": "text",
                        "text": (
                            "Attached file context:\n"
                            f"{attachment_context}\n\n"
                            "Use extracted content when relevant and call out uncertainty if extraction is incomplete."
                        ),
                    }
                )
            content.extend(attachment_blocks)
            messages.append(HumanMessage(content=content))
        else:
            content_parts: list[str] = []
            if user_message:
                content_parts.append(user_message)
            if attachment_context:
                content_parts.append(
                    "Attached file context:\n"
                    f"{attachment_context}\n\n"
                    "Use extracted content when relevant and call out uncertainty if extraction is incomplete."
                )
            messages.append(HumanMessage(content="\n\n".join(content_parts)))
    return messages


@router.get("/stream/schema")
async def stream_schema() -> dict[str, Any]:
    return stream_event_schema()


@router.get("/attachments/{attachment_id}/content")
async def get_attachment_content(
    attachment_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    file_uuid = parse_uuid(attachment_id, field_name="attachment_id")
    row = await session.get(Attachment, file_uuid)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Attachment '{attachment_id}' was not found.")
    path = resolve_storage_path(row.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Attachment file '{attachment_id}' is missing.")
    return FileResponse(path, media_type=row.content_type, filename=row.filename)


@router.post("/attachments", response_model=UploadAttachmentsResponse)
async def upload_attachments(
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> UploadAttachmentsResponse:
    if not files:
        raise HTTPException(status_code=400, detail="Provide at least one file.")

    uploaded: list[StoredAttachment] = []
    for file in files:
        uploaded.append(await store_uploaded_file(file))

    await save_uploaded_attachments(session, uploaded)

    return UploadAttachmentsResponse(
        files=[
            UploadedAttachment(
                id=item.id,
                filename=item.filename,
                content_type=item.content_type,
                media_type=item.media_type,
                size_bytes=item.size_bytes,
                preview_text=item.preview_text,
                extraction_note=item.extraction_note,
            )
            for item in uploaded
        ]
    )


@router.post("", response_model=AgentResponse)
async def run_agent(
    payload: AgentRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    messages = await _build_messages(payload, session)
    if not messages:
        raise HTTPException(status_code=400, detail="Provide message or history.")
    agent = get_agent()
    result = await agent.ainvoke({"messages": messages})
    trace = extract_trace(result["messages"])
    return AgentResponse(**trace)


@router.post("/stream")
async def stream_agent(
    payload: AgentRequest,
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    attachment_ids = [item.strip() for item in (payload.attachment_ids or []) if item.strip()]
    user_message = (payload.message or "").strip()

    if not user_message and not attachment_ids:
        raise HTTPException(status_code=400, detail="Provide message or attachments.")

    try:
        if payload.conversation_id:
            conversation_id = parse_uuid(payload.conversation_id, field_name="conversation_id")
            conversation = await session.get(Conversation, conversation_id)
            if conversation is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation '{payload.conversation_id}' was not found.",
                )
        else:
            conversation = await create_conversation(
                session,
                title=_conversation_title_from_message(user_message),
            )

        persisted_user_content = user_message or "Sent attachments."
        await save_user_message_with_attachments(
            session,
            conversation_id=conversation.id,
            content=persisted_user_content,
            attachment_ids=attachment_ids,
            token_estimate=estimate_tokens(persisted_user_content),
        )
    except AttachmentNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    settings = get_settings()
    context_messages = await build_context_window_for_model(
        session,
        conversation_id=conversation.id,
        max_tokens=settings.context_max_tokens,
        target_tokens=settings.context_target_tokens,
        keep_last_turns=settings.context_keep_last_turns,
    )
    model_messages = [_to_langchain_message(message) for message in context_messages]

    async def _event_stream():
        queue: asyncio.Queue[Any | None] = asyncio.Queue()
        producer_error: Exception | None = None

        async def _push(event: Any) -> None:
            await queue.put(event)

        async def _on_sandbox_status(payload: Any) -> None:
            await _push(
                SandboxStatusEvent(
                    run_id=payload.run_id,
                    stage=payload.stage,
                    message=payload.message,
                    timestamp=payload.timestamp,
                )
            )

        async def _producer() -> None:
            nonlocal producer_error
            agent = get_agent()
            final_ai: AIMessage | None = None
            request_context = AgentRequestContext(
                latest_user_message=user_message,
                latest_user_attachment_ids=tuple(attachment_ids),
            )

            try:
                with bind_event_sink(_on_sandbox_status), bind_request_context(request_context):
                    async for stream_mode, data in agent.astream(
                        {"messages": model_messages},
                        stream_mode=["messages", "updates"],
                    ):
                        if stream_mode == "messages":
                            token, _metadata = data
                            if isinstance(token, AIMessageChunk):
                                extra = getattr(token, "additional_kwargs", None) or {}
                                reasoning_chunk = getattr(
                                    token,
                                    "reasoning_content",
                                    None,
                                ) or extra.get("reasoning_content")
                                if reasoning_chunk:
                                    await _push(ReasoningDeltaEvent(content=str(reasoning_chunk)))
                                for chunk in token.tool_call_chunks:
                                    await _push(
                                        ToolCallDeltaEvent(
                                            id=chunk.get("id"),
                                            name=chunk.get("name"),
                                            args=chunk.get("args"),
                                            index=chunk.get("index"),
                                        )
                                    )
                                content_blocks = getattr(token, "content_blocks", None) or token.content
                                if isinstance(content_blocks, list):
                                    for raw_block in content_blocks:
                                        if not isinstance(raw_block, dict):
                                            continue
                                        block = raw_block
                                        if raw_block.get("type") == "non_standard":
                                            nested = raw_block.get("value")
                                            if isinstance(nested, dict):
                                                block = nested
                                        block_type = block.get("type")
                                        if block_type in {"thinking", "reasoning", "summary"}:
                                            value = (
                                                block.get("thinking")
                                                or block.get("reasoning")
                                                or block.get("summary")
                                            )
                                            if value:
                                                await _push(ReasoningDeltaEvent(content=str(value)))
                                        if block_type in {"text", "output_text"}:
                                            value = block.get("text") or block.get("output_text")
                                            if value:
                                                await _push(TextDeltaEvent(content=str(value)))
                                elif isinstance(content_blocks, str) and content_blocks:
                                    await _push(TextDeltaEvent(content=content_blocks))
                        elif stream_mode == "updates":
                            for _, update in data.items():
                                msg_list = update.get("messages", [])
                                if not msg_list:
                                    continue
                                msg = msg_list[-1]
                                if isinstance(msg, AIMessage):
                                    if msg.tool_calls:
                                        for call in msg.tool_calls:
                                            await _push(
                                                ToolCallEvent(
                                                    id=call.get("id"),
                                                    name=call.get("name"),
                                                    args=call.get("args", {}),
                                                    call_type=call.get("type"),
                                                )
                                            )
                                            await save_assistant_message(
                                                session,
                                                conversation_id=conversation.id,
                                                content=_format_tool_call(call),
                                                message_kind="tool_call",
                                            )
                                    final_ai = msg
                                elif isinstance(msg, ToolMessage):
                                    payload = _parse_tool_result_payload(msg.content)
                                    result_content = _format_tool_result(msg, payload=payload)
                                    artifact_ids = _artifact_attachment_ids(payload)
                                    artifacts = await _tool_result_artifacts(
                                        session,
                                        attachment_ids=artifact_ids,
                                    )

                                    await _push(
                                        ToolResultEvent(
                                            tool_call_id=msg.tool_call_id,
                                            content=result_content,
                                            artifacts=artifacts or None,
                                        )
                                    )
                                    if artifact_ids:
                                        try:
                                            await save_assistant_message_with_attachments(
                                                session,
                                                conversation_id=conversation.id,
                                                content=result_content,
                                                attachment_ids=artifact_ids,
                                                message_kind="tool_result",
                                            )
                                        except AttachmentNotFoundError:
                                            await save_assistant_message(
                                                session,
                                                conversation_id=conversation.id,
                                                content=result_content,
                                                message_kind="tool_result",
                                            )
                                    else:
                                        await save_assistant_message(
                                            session,
                                            conversation_id=conversation.id,
                                            content=result_content,
                                            message_kind="tool_result",
                                        )

                if final_ai is not None:
                    usage = extract_usage(final_ai)
                    response_meta = getattr(final_ai, "response_metadata", None)
                    _, final_text_parts = split_ai_content(final_ai)
                    final_text = "".join(final_text_parts).strip()

                    await save_assistant_message(
                        session,
                        conversation_id=conversation.id,
                        content=final_text or "[empty assistant response]",
                        token_estimate=estimate_tokens(final_text or ""),
                        usage_json=usage if isinstance(usage, dict) else None,
                    )

                    usage_text = _format_meta_block("usage", usage)
                    if usage_text:
                        await save_assistant_message(
                            session,
                            conversation_id=conversation.id,
                            content=usage_text,
                            message_kind="meta",
                        )
                    metadata_text = _format_meta_block("response_metadata", response_meta)
                    if metadata_text:
                        await save_assistant_message(
                            session,
                            conversation_id=conversation.id,
                            content=metadata_text,
                            message_kind="meta",
                        )

                    await _push(
                        FinalEvent(
                            output_text=final_text,
                            usage=usage,
                            response_metadata=response_meta,
                            conversation_id=str(conversation.id),
                        )
                    )
            except Exception as exc:  # pragma: no cover - defensive streaming guard
                producer_error = exc
            finally:
                await queue.put(None)

        producer_task = asyncio.create_task(_producer())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield encode_sse(event)
        finally:
            if not producer_task.done():
                producer_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await producer_task

        if producer_error is not None:
            raise producer_error

    return StreamingResponse(_event_stream(), media_type="text/event-stream")
