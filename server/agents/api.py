from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import get_settings
from server.db.models import Attachment, Conversation, Message
from server.db.session import get_db_session
from server.domain.chat_store import (
    AttachmentNotFoundError,
    ConversationNotFoundError,
    build_context_window_for_model,
    create_conversation,
    estimate_tokens,
    get_conversation_messages,
    list_conversations,
    save_assistant_message,
    save_uploaded_attachments,
    save_user_message_with_attachments,
)

from .attachments import (
    StoredAttachment,
    build_attachment_message_parts_async,
    build_attachment_message_parts_for_items,
    from_db_attachment,
    resolve_storage_path,
    store_uploaded_file,
)
from .openailike_agent import extract_trace, get_agent, split_ai_content
from .streaming_schema import (
    FinalEvent,
    ReasoningDeltaEvent,
    TextDeltaEvent,
    ToolCallDeltaEvent,
    ToolCallEvent,
    ToolResultEvent,
    encode_sse,
    stream_event_schema,
)
from .usage import extract_usage

router = APIRouter(prefix="/api/agent", tags=["agent"])
conversations_router = APIRouter(prefix="/api/conversations", tags=["conversations"])


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


class ConversationSummaryResponse(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_at: datetime | None


class ConversationAttachmentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    media_type: Literal["image", "pdf", "text", "spreadsheet", "binary"]
    size_bytes: int
    preview_text: str | None
    extraction_note: str | None
    position: int
    download_url: str


class ConversationMessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    token_estimate: int
    tokenizer_name: str | None
    message_kind: Literal["normal", "summary", "meta", "tool_call", "tool_result"]
    archived_at: datetime | None
    usage_json: dict[str, Any] | None
    created_at: datetime
    attachments: list[ConversationAttachmentResponse]


class ConversationDetailResponse(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageResponse]


class ContextWindowResponse(BaseModel):
    conversation_id: str
    max_tokens: int
    target_tokens: int
    keep_last_turns: int
    token_sum: int
    messages: list[ConversationMessageResponse]


def _parse_uuid(value: str, *, field_name: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}.") from exc


def _coerce_message_kind(kind: str) -> Literal["normal", "summary", "meta", "tool_call", "tool_result"]:
    allowed = {"normal", "summary", "meta", "tool_call", "tool_result"}
    if kind not in allowed:
        return "meta"
    return kind  # type: ignore[return-value]


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


def _format_tool_result(message: ToolMessage) -> str:
    lines: list[str] = []
    if message.tool_call_id:
        lines.append(f"tool_call_id: {message.tool_call_id}")
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


def _to_message_response(message: Message) -> ConversationMessageResponse:
    attachment_payload: list[ConversationAttachmentResponse] = []
    for link in message.attachment_links:
        attachment = link.attachment
        if attachment is None:
            continue
        attachment_payload.append(
            ConversationAttachmentResponse(
                id=str(attachment.id),
                filename=attachment.filename,
                content_type=attachment.content_type,
                media_type=attachment.media_type,
                size_bytes=attachment.size_bytes,
                preview_text=attachment.preview_text,
                extraction_note=attachment.extraction_note,
                position=link.position,
                download_url=f"/api/agent/attachments/{attachment.id}/content",
            )
        )

    return ConversationMessageResponse(
        id=str(message.id),
        role=message.role,  # type: ignore[arg-type]
        content=message.content,
        token_estimate=message.token_estimate,
        tokenizer_name=message.tokenizer_name,
        message_kind=_coerce_message_kind(message.message_kind),
        archived_at=message.archived_at,
        usage_json=message.usage_json,
        created_at=message.created_at,
        attachments=attachment_payload,
    )


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
    file_uuid = _parse_uuid(attachment_id, field_name="attachment_id")
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
            conversation_id = _parse_uuid(payload.conversation_id, field_name="conversation_id")
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
        agent = get_agent()
        final_ai: AIMessage | None = None

        async for stream_mode, data in agent.astream(
            {"messages": model_messages},
            stream_mode=["messages", "updates"],
        ):
            if stream_mode == "messages":
                token, _metadata = data
                if isinstance(token, AIMessageChunk):
                    extra = getattr(token, "additional_kwargs", None) or {}
                    reasoning_chunk = getattr(token, "reasoning_content", None) or extra.get(
                        "reasoning_content"
                    )
                    if reasoning_chunk:
                        yield encode_sse(ReasoningDeltaEvent(content=str(reasoning_chunk)))
                    for chunk in token.tool_call_chunks:
                        yield encode_sse(
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
                                    yield encode_sse(ReasoningDeltaEvent(content=str(value)))
                            if block_type in {"text", "output_text"}:
                                value = block.get("text") or block.get("output_text")
                                if value:
                                    yield encode_sse(TextDeltaEvent(content=str(value)))
                    elif isinstance(content_blocks, str) and content_blocks:
                        yield encode_sse(TextDeltaEvent(content=content_blocks))
            elif stream_mode == "updates":
                for _, update in data.items():
                    msg_list = update.get("messages", [])
                    if not msg_list:
                        continue
                    msg = msg_list[-1]
                    if isinstance(msg, AIMessage):
                        if msg.tool_calls:
                            for call in msg.tool_calls:
                                event = ToolCallEvent(
                                    id=call.get("id"),
                                    name=call.get("name"),
                                    args=call.get("args", {}),
                                    call_type=call.get("type"),
                                )
                                yield encode_sse(event)
                                await save_assistant_message(
                                    session,
                                    conversation_id=conversation.id,
                                    content=_format_tool_call(call),
                                    message_kind="tool_call",
                                )
                        final_ai = msg
                    elif isinstance(msg, ToolMessage):
                        event = ToolResultEvent(
                            tool_call_id=msg.tool_call_id,
                            content=str(msg.content),
                        )
                        yield encode_sse(event)
                        await save_assistant_message(
                            session,
                            conversation_id=conversation.id,
                            content=_format_tool_result(msg),
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

            yield encode_sse(
                FinalEvent(
                    output_text=final_text,
                    usage=usage,
                    response_metadata=response_meta,
                    conversation_id=str(conversation.id),
                )
            )

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


@conversations_router.get("", response_model=list[ConversationSummaryResponse])
async def get_conversations(
    session: AsyncSession = Depends(get_db_session),
) -> list[ConversationSummaryResponse]:
    rows = await list_conversations(session)
    return [
        ConversationSummaryResponse(
            id=str(item.id),
            title=item.title,
            created_at=item.created_at,
            updated_at=item.updated_at,
            message_count=item.message_count,
            last_message_at=item.last_message_at,
        )
        for item in rows
    ]


@conversations_router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    conversation_uuid = _parse_uuid(conversation_id, field_name="conversation_id")
    conversation = await session.get(Conversation, conversation_uuid)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' was not found.")

    messages = await get_conversation_messages(
        session,
        conversation_uuid,
        include_archived=True,
    )
    return ConversationDetailResponse(
        id=str(conversation.id),
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[_to_message_response(message) for message in messages],
    )


@conversations_router.get(
    "/{conversation_id}/context-window",
    response_model=ContextWindowResponse,
)
async def get_context_window(
    conversation_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ContextWindowResponse:
    conversation_uuid = _parse_uuid(conversation_id, field_name="conversation_id")
    conversation = await session.get(Conversation, conversation_uuid)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' was not found.")

    settings = get_settings()
    messages = await build_context_window_for_model(
        session,
        conversation_id=conversation_uuid,
        max_tokens=settings.context_max_tokens,
        target_tokens=settings.context_target_tokens,
        keep_last_turns=settings.context_keep_last_turns,
    )
    return ContextWindowResponse(
        conversation_id=conversation_id,
        max_tokens=settings.context_max_tokens,
        target_tokens=settings.context_target_tokens,
        keep_last_turns=settings.context_keep_last_turns,
        token_sum=sum(message.token_estimate for message in messages),
        messages=[_to_message_response(message) for message in messages],
    )
