from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from sqlalchemy.ext.asyncio import AsyncSession

from server.features.agent.sandbox.event_bus import (
    AgentRequestContext,
    bind_event_sink,
    bind_request_context,
)
from server.features.agent.sandbox.session_executor import get_conversation_sandbox_status
from server.features.agent.usage import extract_usage
from server.db.models import Attachment, Conversation, Message
from server.features.agent.api.formatters import (
    artifact_attachment_ids,
    format_meta_block,
    format_tool_call,
    format_tool_result,
    parse_tool_result_payload,
)
from server.features.agent.api.message_builders import to_langchain_message
from server.features.agent.api.schemas import AgentRequest
from server.features.agent.schemas import (
    ConversationEvent,
    FinalEvent,
    ReasoningDeltaEvent,
    SandboxStatusEvent,
    TextDeltaEvent,
    ToolCallDeltaEvent,
    ToolCallEvent,
    ToolResultArtifact,
    ToolResultEvent,
    encode_sse,
)
from server.features.agent.service import build_agent, split_ai_content
from server.features.attachments import (
    StoredAttachment,
    load_attachments_for_ids,
    store_uploaded_file,
)
from server.features.chat import (
    AttachmentNotFoundError,
    ConversationNotFoundError,
    append_message_content,
    build_context_window_for_model,
    create_conversation,
    estimate_tokens,
    save_assistant_message,
    save_assistant_message_with_attachments,
    save_uploaded_attachments,
    save_user_message_with_attachments,
)
from server.features.settings.service import (
    resolve_effective_company_profile,
    resolve_effective_model_settings,
)
from server.features.settings.types import CompanyProfileResolved, ModelSettingsResolved
from server.features.shared.ids import parse_uuid


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
    else:
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


async def stream_agent_response(
    payload: AgentRequest,
    *,
    session: AsyncSession,
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
            from server.features.agent.api.formatters import conversation_title_from_message

            conversation = await create_conversation(
                session,
                title=conversation_title_from_message(user_message),
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

    from server.core.config import get_settings

    settings = get_settings()
    model_settings = await resolve_effective_model_settings(session)
    company_profile = await resolve_effective_company_profile(session)
    context_messages = await build_context_window_for_model(
        session,
        conversation_id=conversation.id,
        max_tokens=settings.context_max_tokens,
        target_tokens=settings.context_target_tokens,
        keep_last_turns=settings.context_keep_last_turns,
    )
    model_messages = [to_langchain_message(message) for message in context_messages]
    sandbox_status = await get_conversation_sandbox_status(
        session,
        conversation_id=str(conversation.id),
    )
    model_messages.append(
        HumanMessage(
            content=(
                "Sandbox runtime context (system-generated):\n"
                f"sandbox_session_alive: {'true' if sandbox_status.alive else 'false'}\n"
                f"sandbox_session_id: {sandbox_status.session_id or 'none'}\n"
                f"sandbox_request_sequence: {sandbox_status.request_sequence if sandbox_status.request_sequence is not None else 'none'}\n"
                f"sandbox_available_files: {json.dumps(sandbox_status.available_files, ensure_ascii=True)}\n"
                f"sandbox_status_reason: {sandbox_status.reason}"
            )
        )
    )

    async def _event_stream():
        queue: asyncio.Queue[Any | None] = asyncio.Queue()
        producer_error: Exception | None = None
        active_reasoning_message_id: str | None = None
        active_text_message_id: str | None = None
        streamed_text_buffer = ""

        async def _push(event: Any) -> None:
            await queue.put(event)

        def _close_reasoning_phase() -> None:
            nonlocal active_reasoning_message_id
            active_reasoning_message_id = None

        async def _persist_reasoning_chunk(content: str) -> None:
            nonlocal active_reasoning_message_id
            if not content:
                return

            await _push(ReasoningDeltaEvent(content=content))
            if active_reasoning_message_id is None:
                message = await save_assistant_message(
                    session,
                    conversation_id=conversation.id,
                    content=content,
                    message_kind="reasoning",
                )
                active_reasoning_message_id = str(message.id)
                return

            await append_message_content(
                session,
                message_id=active_reasoning_message_id,
                content_suffix=content,
            )

        async def _persist_text_chunk(content: str) -> None:
            nonlocal active_text_message_id, streamed_text_buffer
            if not content:
                return

            _close_reasoning_phase()
            if active_text_message_id is None:
                message = await save_assistant_message(
                    session,
                    conversation_id=conversation.id,
                    content=content,
                    message_kind="normal",
                )
                active_text_message_id = str(message.id)
                streamed_text_buffer = message.content
            else:
                await append_message_content(
                    session,
                    message_id=active_text_message_id,
                    content_suffix=content,
                )
                streamed_text_buffer = f"{streamed_text_buffer}{content}"

            await _push(TextDeltaEvent(content=content))

        async def _on_sandbox_status(payload: Any) -> None:
            _close_reasoning_phase()
            await _push(
                SandboxStatusEvent(
                    run_id=payload.run_id,
                    stage=payload.stage,
                    message=payload.message,
                    timestamp=payload.timestamp,
                )
            )

        async def _producer() -> None:
            nonlocal producer_error, streamed_text_buffer
            agent = get_agent(model_settings, company_profile)
            final_ai: AIMessage | None = None
            request_context = AgentRequestContext(
                latest_user_message=user_message,
                latest_user_attachment_ids=tuple(attachment_ids),
                conversation_id=str(conversation.id),
            )

            try:
                await _push(ConversationEvent(conversation_id=str(conversation.id)))
                with bind_event_sink(_on_sandbox_status), bind_request_context(request_context):
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
                                    await _persist_reasoning_chunk(str(reasoning_chunk))
                                for chunk in token.tool_call_chunks:
                                    _close_reasoning_phase()
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
                                                await _persist_reasoning_chunk(str(value))
                                        if block_type in {"text", "output_text"}:
                                            value = block.get("text") or block.get("output_text")
                                            if value:
                                                await _persist_text_chunk(str(value))
                                elif isinstance(content_blocks, str) and content_blocks:
                                    await _persist_text_chunk(content_blocks)
                        elif stream_mode == "updates":
                            for _, update in data.items():
                                msg_list = update.get("messages", [])
                                if not msg_list:
                                    continue
                                msg = msg_list[-1]
                                if isinstance(msg, AIMessage):
                                    if msg.tool_calls:
                                        for call in msg.tool_calls:
                                            _close_reasoning_phase()
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
                                                content=format_tool_call(call),
                                                message_kind="tool_call",
                                            )
                                    final_ai = msg
                                elif isinstance(msg, ToolMessage):
                                    tool_payload = parse_tool_result_payload(msg.content)
                                    result_content = format_tool_result(msg, payload=tool_payload)
                                    artifact_ids = artifact_attachment_ids(tool_payload)
                                    artifacts = await _tool_result_artifacts(
                                        session,
                                        attachment_ids=artifact_ids,
                                    )

                                    _close_reasoning_phase()
                                    await _push(
                                        ToolResultEvent(
                                            tool_call_id=msg.tool_call_id,
                                            content=result_content,
                                            artifacts=artifacts or None,
                                            payload=tool_payload,
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
                    _close_reasoning_phase()
                    usage = extract_usage(final_ai)
                    reasoning_tokens = (
                        usage.get("reasoning_tokens")
                        if isinstance(usage, dict) and isinstance(usage.get("reasoning_tokens"), int)
                        else None
                    )
                    response_meta = getattr(final_ai, "response_metadata", None)
                    _, final_text_parts = split_ai_content(final_ai)
                    final_text = "".join(final_text_parts).strip()

                    if active_text_message_id is None:
                        await save_assistant_message(
                            session,
                            conversation_id=conversation.id,
                            content=final_text or "[empty assistant response]",
                            token_estimate=estimate_tokens(final_text or ""),
                            usage_json=usage if isinstance(usage, dict) else None,
                            reasoning_tokens=reasoning_tokens,
                        )
                    elif final_text and final_text.startswith(streamed_text_buffer):
                        suffix = final_text[len(streamed_text_buffer) :]
                        if suffix:
                            await append_message_content(
                                session,
                                message_id=active_text_message_id,
                                content_suffix=suffix,
                            )
                            streamed_text_buffer = final_text

                        text_message = await session.get(
                            Message,
                            UUID(active_text_message_id),
                        )
                        if text_message is not None:
                            text_message.token_estimate = estimate_tokens(text_message.content)
                            text_message.usage_json = usage if isinstance(usage, dict) else None
                            text_message.reasoning_tokens = reasoning_tokens
                            await session.commit()

                    usage_text = format_meta_block("usage", usage)
                    if usage_text:
                        await save_assistant_message(
                            session,
                            conversation_id=conversation.id,
                            content=usage_text,
                            message_kind="meta",
                        )
                    metadata_text = format_meta_block("response_metadata", response_meta)
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


def get_agent(
    model_settings: ModelSettingsResolved,
    company_profile: CompanyProfileResolved,
):
    return build_agent(model_settings, company_profile)
