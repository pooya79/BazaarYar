from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.db.models import Attachment, Conversation, Message, MessageAttachment
from server.features.attachments.schemas import StoredAttachment
from server.features.attachments.service import list_legacy_metadata_attachments

from .constants import DEFAULT_TOKENIZER_NAME
from .errors import AttachmentNotFoundError, ConversationNotFoundError
from .tokens import estimate_tokens
from .types import ConversationListEntry


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
    conversation = Conversation(title=title)
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
    conversation.title = title
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
        attachment = Attachment(
            id=to_uuid(uploaded.id),
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
    conversation = await ensure_conversation(session, conversation_id)
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
) -> Message:
    conversation = await ensure_conversation(session, conversation_id)
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
            Conversation.starred.desc(),
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
                starred=conversation.starred,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                message_count=int(message_count or 0),
                last_message_at=last_message_at,
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

    conversation, message_count, last_message_at = row
    return ConversationListEntry(
        id=conversation.id,
        title=conversation.title,
        starred=conversation.starred,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=int(message_count or 0),
        last_message_at=last_message_at,
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
