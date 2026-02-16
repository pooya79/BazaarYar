from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.db.models import Attachment, Conversation, Message, MessageAttachment
from server.features.attachments.schemas import StoredAttachment
from server.features.attachments.service import list_legacy_metadata_attachments
from server.features.shared.text_sanitize import log_sanitization_stats, sanitize_optional_text

from .constants import DEFAULT_TOKENIZER_NAME
from .errors import AttachmentNotFoundError, ConversationNotFoundError
from .sanitize import sanitize_message_content, sanitize_message_suffix
from .tokens import estimate_tokens
from .types import ConversationListCursor, ConversationListEntry

logger = logging.getLogger(__name__)


def to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)


async def ensure_conversation(session: AsyncSession, conversation_id: UUID | str) -> Conversation:
    conversation = await session.get(Conversation, to_uuid(conversation_id))
    if conversation is None:
        raise ConversationNotFoundError(f"Conversation '{conversation_id}' was not found.")
    return conversation


async def create_conversation(
    session: AsyncSession,
    *,
    title: str | None = None,
) -> Conversation:
    clean_title, title_stats = sanitize_optional_text(title, strip=True)
    log_sanitization_stats(logger, location="chat.create_conversation.title", stats=title_stats)
    conversation = Conversation(title=clean_title)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def rename_conversation(
    session: AsyncSession,
    *,
    conversation_id: UUID | str,
    title: str | None,
) -> Conversation:
    conversation = await ensure_conversation(session, conversation_id)
    clean_title, title_stats = sanitize_optional_text(title, strip=True)
    log_sanitization_stats(logger, location="chat.rename_conversation.title", stats=title_stats)
    conversation.title = clean_title
    conversation.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def set_conversation_starred(
    session: AsyncSession,
    *,
    conversation_id: UUID | str,
    starred: bool,
) -> Conversation:
    conversation = await ensure_conversation(session, conversation_id)
    conversation.starred = starred
    conversation.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def delete_conversation(
    session: AsyncSession,
    *,
    conversation_id: UUID | str,
) -> None:
    conversation = await ensure_conversation(session, conversation_id)
    await session.delete(conversation)
    await session.commit()


async def save_uploaded_attachments(
    session: AsyncSession,
    uploaded_files: Sequence[StoredAttachment],
) -> list[Attachment]:
    saved: list[Attachment] = []
    for uploaded in uploaded_files:
        preview_text, preview_stats = sanitize_optional_text(uploaded.preview_text, strip=False)
        extraction_note, note_stats = sanitize_optional_text(uploaded.extraction_note, strip=False)
        log_sanitization_stats(
            logger,
            location="chat.save_uploaded_attachments.preview_text",
            stats=preview_stats,
        )
        log_sanitization_stats(
            logger,
            location="chat.save_uploaded_attachments.extraction_note",
            stats=note_stats,
        )
        attachment = Attachment(
            id=to_uuid(uploaded.id),
            filename=uploaded.filename,
            content_type=uploaded.content_type,
            media_type=uploaded.media_type,
            size_bytes=uploaded.size_bytes,
            storage_path=uploaded.storage_path,
            preview_text=preview_text,
            extraction_note=extraction_note,
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

    legacy_ids = [to_uuid(item.id) for item in legacy_items]
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
        attachment_id = to_uuid(item.id)
        if attachment_id in existing:
            continue
        preview_text, preview_stats = sanitize_optional_text(item.preview_text, strip=False)
        extraction_note, note_stats = sanitize_optional_text(item.extraction_note, strip=False)
        log_sanitization_stats(
            logger,
            location="chat.backfill_attachments.preview_text",
            stats=preview_stats,
        )
        log_sanitization_stats(
            logger,
            location="chat.backfill_attachments.extraction_note",
            stats=note_stats,
        )
        session.add(
            Attachment(
                id=attachment_id,
                filename=item.filename,
                content_type=item.content_type,
                media_type=item.media_type,
                size_bytes=item.size_bytes,
                storage_path=item.storage_path,
                preview_text=preview_text,
                extraction_note=extraction_note,
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
    conversation = await ensure_conversation(session, conversation_id)
    clean_content = sanitize_message_content(
        content,
        strip=True,
        location="chat.save_user_message_with_attachments.content",
    )

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
        attachment_uuid_ids = [to_uuid(item) for item in clean_ids]
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
    reasoning_tokens: int | None = None,
) -> Message:
    conversation = await ensure_conversation(session, conversation_id)
    clean_content = sanitize_message_content(
        content,
        strip=message_kind != "reasoning",
        location=f"chat.save_assistant_message.content.{message_kind}",
    )
    message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=clean_content,
        token_estimate=token_estimate if token_estimate is not None else estimate_tokens(clean_content),
        tokenizer_name=tokenizer_name,
        message_kind=message_kind,
        usage_json=usage_json,
        reasoning_tokens=reasoning_tokens,
    )
    session.add(message)
    conversation.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(message)
    return message


async def append_message_content(
    session: AsyncSession,
    *,
    message_id: UUID | str,
    content_suffix: str,
) -> Message:
    message = await session.get(Message, to_uuid(message_id))
    if message is None:
        raise ValueError(f"Message '{message_id}' was not found.")

    message.content = (
        f"{message.content}"
        f"{sanitize_message_suffix(content_suffix, location='chat.append_message_content.content_suffix')}"
    )
    await session.commit()
    await session.refresh(message)
    return message


async def save_assistant_message_with_attachments(
    session: AsyncSession,
    *,
    conversation_id: UUID | str,
    content: str,
    attachment_ids: Sequence[str],
    token_estimate: int | None = None,
    tokenizer_name: str = DEFAULT_TOKENIZER_NAME,
    message_kind: str = "tool_result",
    usage_json: dict[str, Any] | None = None,
) -> Message:
    conversation = await ensure_conversation(session, conversation_id)
    clean_content = sanitize_message_content(
        content,
        strip=True,
        location="chat.save_assistant_message_with_attachments.content",
    )
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
    await session.flush()

    clean_ids = [item.strip() for item in attachment_ids if item.strip()]
    if clean_ids:
        attachment_uuid_ids = [to_uuid(item) for item in clean_ids]
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


async def list_conversations(
    session: AsyncSession,
    *,
    limit: int = 100,
    cursor: ConversationListCursor | None = None,
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
    sort_at = func.coalesce(message_stats.c.last_message_at, Conversation.updated_at).label(
        "sort_at"
    )

    stmt = (
        select(
            Conversation,
            message_stats.c.message_count,
            message_stats.c.last_message_at,
            sort_at,
        )
        .outerjoin(
            message_stats,
            message_stats.c.conversation_id == Conversation.id,
        )
        .order_by(
            Conversation.starred.desc(),
            sort_at.desc(),
            Conversation.created_at.desc(),
            Conversation.id.desc(),
        )
        .limit(limit + 1)
    )
    if cursor is not None:
        starred_transition = (
            Conversation.starred.is_(False) if cursor.starred else false()
        )
        stmt = stmt.where(
            or_(
                starred_transition,
                and_(
                    Conversation.starred.is_(cursor.starred),
                    sort_at < cursor.sort_at,
                ),
                and_(
                    Conversation.starred.is_(cursor.starred),
                    sort_at == cursor.sort_at,
                    Conversation.created_at < cursor.created_at,
                ),
                and_(
                    Conversation.starred.is_(cursor.starred),
                    sort_at == cursor.sort_at,
                    Conversation.created_at == cursor.created_at,
                    Conversation.id < cursor.id,
                ),
            )
        )
    rows = (await session.execute(stmt)).all()

    output: list[ConversationListEntry] = []
    for conversation, message_count, last_message_at, sort_at_value in rows:
        output.append(
            ConversationListEntry(
                id=conversation.id,
                title=conversation.title,
                starred=conversation.starred,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                message_count=int(message_count or 0),
                last_message_at=last_message_at,
                sort_at=sort_at_value,
            )
        )
    return output


async def get_conversation_summary(
    session: AsyncSession,
    *,
    conversation_id: UUID | str,
) -> ConversationListEntry:
    conversation_uuid = to_uuid(conversation_id)
    message_stats = (
        select(
            Message.conversation_id.label("conversation_id"),
            func.count(Message.id).label("message_count"),
            func.max(Message.created_at).label("last_message_at"),
        )
        .where(Message.conversation_id == conversation_uuid)
        .group_by(Message.conversation_id)
        .subquery()
    )

    stmt = (
        select(
            Conversation,
            message_stats.c.message_count,
            message_stats.c.last_message_at,
            func.coalesce(message_stats.c.last_message_at, Conversation.updated_at).label("sort_at"),
        )
        .outerjoin(
            message_stats,
            message_stats.c.conversation_id == Conversation.id,
        )
        .where(Conversation.id == conversation_uuid)
    )
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        raise ConversationNotFoundError(f"Conversation '{conversation_id}' was not found.")

    conversation, message_count, last_message_at, sort_at = row
    return ConversationListEntry(
        id=conversation.id,
        title=conversation.title,
        starred=conversation.starred,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=int(message_count or 0),
        last_message_at=last_message_at,
        sort_at=sort_at,
    )


async def get_conversation_messages(
    session: AsyncSession,
    conversation_id: UUID | str,
    *,
    include_archived: bool = True,
) -> list[Message]:
    await ensure_conversation(session, conversation_id)

    stmt = (
        select(Message)
        .where(Message.conversation_id == to_uuid(conversation_id))
        .options(
            selectinload(Message.attachment_links).selectinload(MessageAttachment.attachment),
        )
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    if not include_archived:
        stmt = stmt.where(Message.archived_at.is_(None))

    result = await session.execute(stmt)
    return list(result.scalars().all())
