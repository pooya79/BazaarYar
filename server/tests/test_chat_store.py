from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from server.db.models import Message
from server.domain import chat_store


class _FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True

    async def refresh(self, item):
        self.refreshed.append(item)


def _build_messages(turns: int, token_per_message: int = 40):
    conversation_id = uuid4()
    base = datetime.now(timezone.utc) - timedelta(minutes=turns * 2)
    output: list[Message] = []
    for turn in range(turns):
        user_message = Message(
            id=uuid4(),
            conversation_id=conversation_id,
            role="user",
            content=f"user-{turn}",
            token_estimate=token_per_message,
            tokenizer_name="char4_approx_v1",
            message_kind="normal",
            created_at=base + timedelta(minutes=turn * 2),
        )
        assistant_message = Message(
            id=uuid4(),
            conversation_id=conversation_id,
            role="assistant",
            content=f"assistant-{turn}",
            token_estimate=token_per_message,
            tokenizer_name="char4_approx_v1",
            message_kind="normal",
            created_at=base + timedelta(minutes=turn * 2 + 1),
        )
        output.extend([user_message, assistant_message])
    return conversation_id, output


def test_context_builder_respects_budget_and_keep_last_turns(monkeypatch):
    conversation_id, messages = _build_messages(turns=4, token_per_message=40)

    async def _fake_get_messages(_session, _conversation_id, *, include_archived=True):
        _ = include_archived
        assert str(_conversation_id) == str(conversation_id)
        return messages

    monkeypatch.setattr(chat_store, "get_conversation_messages", _fake_get_messages)

    selected = asyncio.run(
        chat_store.build_context_window_for_model(
            _FakeSession(),
            conversation_id=conversation_id,
            max_tokens=200,
            target_tokens=100,
            keep_last_turns=1,
        )
    )

    # Last turn is always retained (2 messages), and budget blocks older turns.
    assert len(selected) == 2
    assert selected[0].content == "user-3"
    assert selected[1].content == "assistant-3"


def test_summary_compaction_archives_old_messages(monkeypatch):
    conversation_id, messages = _build_messages(turns=4, token_per_message=50)

    async def _fake_get_messages(_session, _conversation_id, *, include_archived=True):
        _ = include_archived
        assert str(_conversation_id) == str(conversation_id)
        return messages

    monkeypatch.setattr(chat_store, "get_conversation_messages", _fake_get_messages)
    session = _FakeSession()

    summary = asyncio.run(
        chat_store.summarize_and_archive_old_messages(
            session,
            conversation_id=conversation_id,
            summarize_fn=lambda span: f"Summary of {len(span)} messages",
            max_tokens=200,
            target_tokens=120,
            keep_last_turns=1,
        )
    )

    assert summary is not None
    assert summary.message_kind == "summary"
    assert session.committed is True
    archived = [message for message in messages if message.archived_at is not None]
    # Old span should be archived, latest turn should remain raw.
    assert len(archived) == 6
    assert messages[-1].archived_at is None
    assert messages[-2].archived_at is None
