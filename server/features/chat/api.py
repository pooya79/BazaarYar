from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.features.shared.ids import parse_uuid
from server.core.config import get_settings
from server.db.models import Conversation, Message
from server.db.session import get_db_session
from server.features.chat import (
    ConversationListCursor,
    ConversationListEntry,
    ConversationNotFoundError,
    build_context_window_for_model,
    delete_conversation,
    get_conversation_summary,
    get_conversation_messages,
    list_conversations,
    rename_conversation,
    set_conversation_starred,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationSummaryResponse(BaseModel):
    id: str
    title: str | None
    starred: bool
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_at: datetime | None


class ConversationListPageResponse(BaseModel):
    items: list[ConversationSummaryResponse]
    next_cursor: str | None
    has_more: bool


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
    message_kind: Literal["normal", "summary", "meta", "reasoning", "tool_call", "tool_result"]
    archived_at: datetime | None
    usage_json: dict[str, Any] | None
    reasoning_tokens: int | None
    created_at: datetime
    attachments: list[ConversationAttachmentResponse]


class ConversationDetailResponse(BaseModel):
    id: str
    title: str | None
    starred: bool
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


class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class StarConversationRequest(BaseModel):
    starred: bool


def _coerce_message_kind(
    kind: str,
) -> Literal["normal", "summary", "meta", "reasoning", "tool_call", "tool_result"]:
    allowed = {"normal", "summary", "meta", "reasoning", "tool_call", "tool_result"}
    if kind not in allowed:
        return "meta"
    return kind  # type: ignore[return-value]


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
        reasoning_tokens=message.reasoning_tokens,
        created_at=message.created_at,
        attachments=attachment_payload,
    )


def _to_summary_response(item: ConversationListEntry) -> ConversationSummaryResponse:
    return ConversationSummaryResponse(
        id=str(item.id),
        title=item.title,
        starred=item.starred,
        created_at=item.created_at,
        updated_at=item.updated_at,
        message_count=item.message_count,
        last_message_at=item.last_message_at,
    )


def _encode_cursor(cursor: ConversationListCursor) -> str:
    payload = {
        "starred": cursor.starred,
        "sort_at": cursor.sort_at.astimezone(timezone.utc).isoformat(),
        "created_at": cursor.created_at.astimezone(timezone.utc).isoformat(),
        "id": str(cursor.id),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return encoded.decode("ascii").rstrip("=")


def _decode_cursor(raw_cursor: str) -> ConversationListCursor:
    padded = raw_cursor + "=" * (-len(raw_cursor) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
        starred = payload["starred"]
        sort_at = datetime.fromisoformat(payload["sort_at"])
        created_at = datetime.fromisoformat(payload["created_at"])
        item_id = UUID(payload["id"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, binascii.Error) as exc:
        raise ValueError("Invalid pagination cursor.") from exc

    if not isinstance(starred, bool):
        raise ValueError("Invalid pagination cursor.")
    if sort_at.tzinfo is None or created_at.tzinfo is None:
        raise ValueError("Invalid pagination cursor.")

    return ConversationListCursor(
        starred=starred,
        sort_at=sort_at,
        created_at=created_at,
        id=item_id,
    )


@router.get("", response_model=ConversationListPageResponse)
async def get_conversations(
    limit: int = Query(default=30, ge=1, le=100),
    cursor: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationListPageResponse:
    decoded_cursor: ConversationListCursor | None = None
    if cursor:
        try:
            decoded_cursor = _decode_cursor(cursor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    rows = await list_conversations(
        session,
        limit=limit,
        cursor=decoded_cursor,
    )
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = None
    if has_more and page_rows:
        last_item = page_rows[-1]
        next_cursor = _encode_cursor(
            ConversationListCursor(
                starred=last_item.starred,
                sort_at=last_item.sort_at,
                created_at=last_item.created_at,
                id=last_item.id,
            )
        )
    return ConversationListPageResponse(
        items=[_to_summary_response(item) for item in page_rows],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    conversation_uuid = parse_uuid(conversation_id, field_name="conversation_id")
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
        starred=conversation.starred,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[_to_message_response(message) for message in messages],
    )


@router.get(
    "/{conversation_id}/context-window",
    response_model=ContextWindowResponse,
)
async def get_context_window(
    conversation_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ContextWindowResponse:
    conversation_uuid = parse_uuid(conversation_id, field_name="conversation_id")
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


@router.patch("/{conversation_id}/title", response_model=ConversationSummaryResponse)
async def patch_conversation_title(
    conversation_id: str,
    payload: RenameConversationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ConversationSummaryResponse:
    conversation_uuid = parse_uuid(conversation_id, field_name="conversation_id")
    normalized_title = payload.title.strip()
    if not normalized_title:
        raise HTTPException(status_code=400, detail="Conversation title cannot be empty.")
    try:
        conversation = await rename_conversation(
            session,
            conversation_id=conversation_uuid,
            title=normalized_title,
        )
        summary = await get_conversation_summary(session, conversation_id=conversation.id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_summary_response(summary)


@router.patch("/{conversation_id}/star", response_model=ConversationSummaryResponse)
async def patch_conversation_star(
    conversation_id: str,
    payload: StarConversationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ConversationSummaryResponse:
    conversation_uuid = parse_uuid(conversation_id, field_name="conversation_id")
    try:
        conversation = await set_conversation_starred(
            session,
            conversation_id=conversation_uuid,
            starred=payload.starred,
        )
        summary = await get_conversation_summary(session, conversation_id=conversation.id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_summary_response(summary)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    conversation_uuid = parse_uuid(conversation_id, field_name="conversation_id")
    try:
        await delete_conversation(session, conversation_id=conversation_uuid)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
