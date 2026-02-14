from __future__ import annotations

from datetime import datetime, timezone
from inspect import isawaitable
from typing import Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import Message

from .constants import DEFAULT_TOKENIZER_NAME, MODEL_CONTEXT_MESSAGE_KINDS
from .errors import AttachmentNotFoundError, ConversationNotFoundError
from .repo import (
    append_message_content,
    backfill_attachments_from_legacy_json,
    create_conversation,
    delete_conversation,
    get_conversation_summary,
    get_conversation_messages,
    list_conversations,
    rename_conversation,
    save_assistant_message,
    save_assistant_message_with_attachments,
    save_uploaded_attachments,
    save_user_message_with_attachments,
    set_conversation_starred,
    to_uuid,
)
from .selection import model_relevant_messages, pick_messages_for_budget
from .tokens import estimate_tokens
from .types import ConversationListCursor, ConversationListEntry


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
    relevant_messages = model_relevant_messages(messages)
    selected, _ = pick_messages_for_budget(
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
    relevant_messages = model_relevant_messages(messages)
    _, omitted = pick_messages_for_budget(
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
        conversation_id=to_uuid(conversation_id),
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


__all__ = [
    "AttachmentNotFoundError",
    "ConversationListEntry",
    "ConversationListCursor",
    "ConversationNotFoundError",
    "DEFAULT_TOKENIZER_NAME",
    "MODEL_CONTEXT_MESSAGE_KINDS",
    "append_message_content",
    "backfill_attachments_from_legacy_json",
    "build_context_window_for_model",
    "create_conversation",
    "delete_conversation",
    "estimate_tokens",
    "get_conversation_summary",
    "get_conversation_messages",
    "list_conversations",
    "rename_conversation",
    "save_assistant_message",
    "save_assistant_message_with_attachments",
    "save_uploaded_attachments",
    "save_user_message_with_attachments",
    "set_conversation_starred",
    "summarize_and_archive_old_messages",
]
