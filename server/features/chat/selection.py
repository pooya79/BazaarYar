from __future__ import annotations

from typing import Sequence
from uuid import UUID

from server.db.models import Message

from .constants import MODEL_CONTEXT_MESSAGE_KINDS
from .tokens import token_value


def model_relevant_messages(messages: Sequence[Message]) -> list[Message]:
    return [
        message
        for message in messages
        if message.archived_at is None and message.message_kind in MODEL_CONTEXT_MESSAGE_KINDS
    ]


def select_required_recent_messages(
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


def pick_messages_for_budget(
    messages: Sequence[Message],
    *,
    max_tokens: int,
    target_tokens: int,
    keep_last_turns: int,
) -> tuple[list[Message], list[Message]]:
    ordered = list(messages)
    if not ordered:
        return [], []

    required_ids = select_required_recent_messages(ordered, keep_last_turns=keep_last_turns)
    selected_ids = set(required_ids)
    token_used = sum(token_value(message) for message in ordered if message.id in required_ids)

    older_messages = [message for message in ordered if message.id not in required_ids]
    # Prefer newer historical context first once required recent turns are included.
    for message in reversed(older_messages):
        tokens = token_value(message)
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
            tokens = token_value(message)
            if remaining - tokens >= max_tokens:
                remaining -= tokens
                omitted.append(message)
                continue
            trimmed_selected.append(message)
        selected = trimmed_selected

    return selected, omitted
