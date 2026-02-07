from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from inspect import isawaitable
from typing import Any, Awaitable, Callable, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.agents.attachments import StoredAttachment, list_legacy_metadata_attachments
from server.db.models import Attachment, Conversation, Message, MessageAttachment

DEFAULT_TOKENIZER_NAME = "char4_approx_v1"
MODEL_CONTEXT_MESSAGE_KINDS = {"normal", "summary", "tool_call", "tool_result"}


class ConversationNotFoundError(ValueError):
    pass


class AttachmentNotFoundError(ValueError):
    pass


@dataclass(frozen=True)
class ConversationListEntry:
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_at: datetime | None


def estimate_tokens(text: str) -> int:
    compact = text.strip()
    if not compact:
        return 1
    return max(1, math.ceil(len(compact) / 4))


def _to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)


async def _ensure_conversation(session: AsyncSession, conversation_id: UUID | str) -> Conversation:
    conversation = await session.get(Conversation, _to_uuid(conversation_id))
    if conversation is None:
        raise ConversationNotFoundError(f"Conversation '{conversation_id}' was not found.")
    return conversation


def _token_value(message: Message) -> int:
    if message.token_estimate > 0:
        return int(message.token_estimate)
    return estimate_tokens(message.content)


def _model_relevant_messages(messages: Sequence[Message]) -> list[Message]:
    return [
        message
        for message in messages
        if message.archived_at is None and message.message_kind in MODEL_CONTEXT_MESSAGE_KINDS
    ]


def _select_required_recent_messages(
    messages: Sequence[Message],
    *,
    keep_last_turns: int,
) -> set[UUID]:
    if keep_last_turns <= 0:
        return set()

    required: set[UUID] = set()
    user_turns = 0
    for message in reversed(messages):
        required.add(message.id)
        if message.role == "user":
            user_turns += 1
            if user_turns >= keep_last_turns:
                break
    return required


def _pick_messages_for_budget(
    messages: Sequence[Message],
    *,
    max_tokens: int,
    target_tokens: int,
    keep_last_turns: int,
) -> tuple[list[Message], list[Message]]:
    ordered = list(messages)
    if not ordered:
        return [], []

    required_ids = _select_required_recent_messages(ordered, keep_last_turns=keep_last_turns)
    selected_ids = set(required_ids)
    token_used = sum(_token_value(message) for message in ordered if message.id in required_ids)

    older_messages = [message for message in ordered if message.id not in required_ids]
    # Prefer newer historical context first once required recent turns are included.
    for message in reversed(older_messages):
        tokens = _token_value(message)
        if token_used + tokens > target_tokens:
            continue
        selected_ids.add(message.id)
        token_used += tokens

    selected = [message for message in ordered if message.id in selected_ids]
    omitted = [message for message in ordered if message.id not in selected_ids]

    if token_used > max_tokens:
        trimmed_selected: list[Message] = []
        remaining = token_used
        for message in selected:
            if message.id in required_ids:
                trimmed_selected.append(message)
                continue
            tokens = _token_value(message)
            if remaining - tokens >= max_tokens:
                remaining -= tokens
                omitted.append(message)
                continue
            trimmed_selected.append(message)
        selected = trimmed_selected

    return selected, omitted


async def create_conversation(
    session: AsyncSession,
    *,
    title: str | None = None,
) -> Conversation:
    conversation = Conversation(title=title)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def save_uploaded_attachments(
    session: AsyncSession,
    uploaded_files: Sequence[StoredAttachment],
) -> list[Attachment]:
    saved: list[Attachment] = []
    for uploaded in uploaded_files:
        attachment = Attachment(
            id=_to_uuid(uploaded.id),
            filename=uploaded.filename,
            content_type=uploaded.content_type,
            media_type=uploaded.media_type,
            size_bytes=uploaded.size_bytes,
            storage_path=uploaded.storage_path,
            preview_text=uploaded.preview_text,
            extraction_note=uploaded.extraction_note,
            created_at=uploaded.created_at,
        )
        session.add(attachment)
        saved.append(attachment)
    await session.commit()
    return saved


async def backfill_attachments_from_legacy_json(session: AsyncSession) -> int:
    legacy_items = list_legacy_metadata_attachments()
    if not legacy_items:
        return 0

    legacy_ids = [_to_uuid(item.id) for item in legacy_items]
    existing = {
        item
        for item in (
            await session.execute(
                select(Attachment.id).where(Attachment.id.in_(legacy_ids))
            )
        )
        .scalars()
        .all()
    }

    created = 0
    for item in legacy_items:
        attachment_id = _to_uuid(item.id)
        if attachment_id in existing:
            continue
        session.add(
            Attachment(
                id=attachment_id,
                filename=item.filename,
                content_type=item.content_type,
                media_type=item.media_type,
                size_bytes=item.size_bytes,
                storage_path=item.storage_path,
                preview_text=item.preview_text,
                extraction_note=item.extraction_note,
                created_at=item.created_at,
            )
        )
        created += 1

    if created:
        await session.commit()
    return created


async def save_user_message_with_attachments(
    session: AsyncSession,
    *,
    conversation_id: UUID | str,
    content: str,
    attachment_ids: Sequence[str] | None = None,
    token_estimate: int | None = None,
    tokenizer_name: str = DEFAULT_TOKENIZER_NAME,
    message_kind: str = "normal",
) -> Message:
    conversation = await _ensure_conversation(session, conversation_id)
    clean_content = content.strip()

    message = Message(
        conversation_id=conversation.id,
        role="user",
        content=clean_content,
        token_estimate=token_estimate if token_estimate is not None else estimate_tokens(clean_content),
        tokenizer_name=tokenizer_name,
        message_kind=message_kind,
    )
    session.add(message)
    await session.flush()

    clean_ids = [item.strip() for item in (attachment_ids or []) if item.strip()]
    if clean_ids:
        attachment_uuid_ids = [_to_uuid(item) for item in clean_ids]
        stmt = select(Attachment).where(Attachment.id.in_(attachment_uuid_ids))
        result = await session.execute(stmt)
        attachments = {str(item.id): item for item in result.scalars().all()}
        missing = [item for item in clean_ids if item not in attachments]
        if missing:
            raise AttachmentNotFoundError(f"Attachment(s) not found: {', '.join(missing)}")

        for index, attachment_id in enumerate(clean_ids):
            session.add(
                MessageAttachment(
                    message_id=message.id,
                    attachment_id=attachments[attachment_id].id,
                    position=index,
                )
            )

    conversation.updated_at = datetime.now(timezone.utc)
    await session.commit()

    stmt = (
        select(Message)
        .where(Message.id == message.id)
        .options(
            selectinload(Message.attachment_links).selectinload(MessageAttachment.attachment),
        )
    )
    refreshed = (await session.execute(stmt)).scalar_one()
    return refreshed


async def save_assistant_message(
    session: AsyncSession,
    *,
    conversation_id: UUID | str,
    content: str,
    token_estimate: int | None = None,
    tokenizer_name: str = DEFAULT_TOKENIZER_NAME,
    message_kind: str = "normal",
    usage_json: dict[str, Any] | None = None,
) -> Message:
    conversation = await _ensure_conversation(session, conversation_id)
    clean_content = content.strip()
    message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=clean_content,
        token_estimate=token_estimate if token_estimate is not None else estimate_tokens(clean_content),
        tokenizer_name=tokenizer_name,
        message_kind=message_kind,
        usage_json=usage_json,
    )
    session.add(message)
    conversation.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(message)
    return message


async def list_conversations(
    session: AsyncSession,
    *,
    limit: int = 100,
) -> list[ConversationListEntry]:
    message_stats = (
        select(
            Message.conversation_id.label("conversation_id"),
            func.count(Message.id).label("message_count"),
            func.max(Message.created_at).label("last_message_at"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    stmt = (
        select(
            Conversation,
            message_stats.c.message_count,
            message_stats.c.last_message_at,
        )
        .outerjoin(
            message_stats,
            message_stats.c.conversation_id == Conversation.id,
        )
        .order_by(
            func.coalesce(message_stats.c.last_message_at, Conversation.updated_at).desc(),
            Conversation.created_at.desc(),
        )
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()

    output: list[ConversationListEntry] = []
    for conversation, message_count, last_message_at in rows:
        output.append(
            ConversationListEntry(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                message_count=int(message_count or 0),
                last_message_at=last_message_at,
            )
        )
    return output


async def get_conversation_messages(
    session: AsyncSession,
    conversation_id: UUID | str,
    *,
    include_archived: bool = True,
) -> list[Message]:
    await _ensure_conversation(session, conversation_id)

    stmt = (
        select(Message)
        .where(Message.conversation_id == _to_uuid(conversation_id))
        .options(
            selectinload(Message.attachment_links).selectinload(MessageAttachment.attachment),
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    if not include_archived:
        stmt = stmt.where(Message.archived_at.is_(None))

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def build_context_window_for_model(
    session: AsyncSession,
    *,
    conversation_id: UUID | str,
    max_tokens: int,
    target_tokens: int,
    keep_last_turns: int,
) -> list[Message]:
    messages = await get_conversation_messages(
        session,
        conversation_id,
        include_archived=False,
    )
    relevant_messages = _model_relevant_messages(messages)
    selected, _ = _pick_messages_for_budget(
        relevant_messages,
        max_tokens=max_tokens,
        target_tokens=min(target_tokens, max_tokens),
        keep_last_turns=keep_last_turns,
    )
    return selected


async def summarize_and_archive_old_messages(
    session: AsyncSession,
    *,
    conversation_id: UUID | str,
    summarize_fn: Callable[[list[Message]], str | Awaitable[str]],
    max_tokens: int,
    target_tokens: int,
    keep_last_turns: int,
    tokenizer_name: str = DEFAULT_TOKENIZER_NAME,
) -> Message | None:
    messages = await get_conversation_messages(
        session,
        conversation_id,
        include_archived=False,
    )
    relevant_messages = _model_relevant_messages(messages)
    _, omitted = _pick_messages_for_budget(
        relevant_messages,
        max_tokens=max_tokens,
        target_tokens=min(target_tokens, max_tokens),
        keep_last_turns=keep_last_turns,
    )

    if not omitted:
        return None

    summary_input = [message for message in omitted if message.message_kind != "summary"]
    if not summary_input:
        return None

    summary_result = summarize_fn(summary_input)
    if isawaitable(summary_result):
        summary_text = await summary_result
    else:
        summary_text = summary_result

    summary_text = summary_text.strip()
    if not summary_text:
        return None

    now = datetime.now(timezone.utc)
    for message in summary_input:
        message.archived_at = now

    summary_message = Message(
        conversation_id=_to_uuid(conversation_id),
        role="assistant",
        content=summary_text,
        message_kind="summary",
        token_estimate=estimate_tokens(summary_text),
        tokenizer_name=tokenizer_name,
    )
    session.add(summary_message)
    await session.commit()
    await session.refresh(summary_message)
    return summary_message
