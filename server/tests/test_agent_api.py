from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage

from server.agents import api as agent_api
from server.domain.chat_store import ConversationListEntry
from server.main import app


class _StubAgent:
    def __init__(self):
        self.last_payload = None

    async def ainvoke(self, payload):
        self.last_payload = payload
        tool_call = {
            "id": "call-1",
            "name": "utc_time",
            "args": {},
            "type": "tool_call",
        }
        ai_msg = AIMessage(
            content=[
                {"type": "thinking", "thinking": "Checking time."},
                {"type": "text", "text": "I'll fetch the time."},
            ],
            tool_calls=[tool_call],
            usage_metadata={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
            response_metadata={"model_name": "gpt-4.1-mini"},
        )
        tool_msg = ToolMessage(content="2026-02-03T00:00:00Z", tool_call_id="call-1")
        final_msg = AIMessage(
            content=[{"type": "text", "text": "It is 2026-02-03T00:00:00Z."}],
            usage_metadata={"input_tokens": 2, "output_tokens": 5, "total_tokens": 7},
            response_metadata={"model_name": "gpt-4.1-mini"},
        )
        return {"messages": [*payload["messages"], ai_msg, tool_msg, final_msg]}

    async def astream(self, payload, stream_mode=("messages", "updates")):
        self.last_payload = payload
        tool_call = {
            "id": "call-1",
            "name": "utc_time",
            "args": {},
            "type": "tool_call",
        }
        ai_msg = AIMessage(
            content=[{"type": "text", "text": "Let me check."}],
            tool_calls=[tool_call],
            usage_metadata={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
            response_metadata={"model_name": "gpt-4.1-mini"},
        )
        tool_msg = ToolMessage(content="2026-02-03T00:00:00Z", tool_call_id="call-1")
        final_msg = AIMessage(
            content=[{"type": "text", "text": "Done."}],
            usage_metadata={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            response_metadata={"model_name": "gpt-4.1-mini"},
        )
        if "messages" in stream_mode:
            from langchain_core.messages import AIMessageChunk

            chunk = AIMessageChunk(content=[{"type": "text", "text": "Done"}])
            yield ("messages", (chunk, {"langgraph_node": "model"}))
        if "updates" in stream_mode:
            yield ("updates", {"model": {"messages": [*payload["messages"], ai_msg]}})
            yield ("updates", {"tools": {"messages": [tool_msg]}})
            yield ("updates", {"model": {"messages": [final_msg]}})


class _MemoryStore:
    def __init__(self):
        self.conversations: dict[str, SimpleNamespace] = {}
        self.messages: dict[str, list[SimpleNamespace]] = {}
        self.attachments: dict[str, SimpleNamespace] = {}

    async def create_conversation(self, _session, *, title=None):
        now = datetime.now(timezone.utc)
        conversation_id = uuid4()
        conversation = SimpleNamespace(
            id=conversation_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        self.conversations[str(conversation_id)] = conversation
        self.messages[str(conversation_id)] = []
        return conversation

    async def save_uploaded_attachments(self, _session, uploaded):
        for item in uploaded:
            attachment_id = item.id
            self.attachments[str(attachment_id)] = SimpleNamespace(
                id=UUID(str(attachment_id)),
                filename=item.filename,
                content_type=item.content_type,
                media_type=item.media_type,
                size_bytes=item.size_bytes,
                storage_path=item.storage_path,
                preview_text=item.preview_text,
                extraction_note=item.extraction_note,
                created_at=item.created_at,
            )
        return list(self.attachments.values())

    async def save_user_message_with_attachments(
        self,
        _session,
        *,
        conversation_id,
        content,
        attachment_ids=None,
        token_estimate=0,
        tokenizer_name="char4_approx_v1",
        message_kind="normal",
    ):
        return self._save_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
            message_kind=message_kind,
            token_estimate=token_estimate,
            tokenizer_name=tokenizer_name,
            attachment_ids=attachment_ids or [],
        )

    async def save_assistant_message(
        self,
        _session,
        *,
        conversation_id,
        content,
        token_estimate=0,
        tokenizer_name="char4_approx_v1",
        message_kind="normal",
        usage_json=None,
    ):
        return self._save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            message_kind=message_kind,
            token_estimate=token_estimate,
            tokenizer_name=tokenizer_name,
            usage_json=usage_json,
            attachment_ids=[],
        )

    def _save_message(
        self,
        *,
        conversation_id,
        role,
        content,
        message_kind,
        token_estimate,
        tokenizer_name,
        attachment_ids,
        usage_json=None,
    ):
        conversation_key = str(conversation_id)
        now = datetime.now(timezone.utc)
        links = []
        for index, attachment_id in enumerate(attachment_ids):
            attachment = self.attachments.get(attachment_id)
            if attachment is None:
                raise ValueError(f"Attachment '{attachment_id}' not found")
            links.append(SimpleNamespace(position=index, attachment=attachment))
        message = SimpleNamespace(
            id=uuid4(),
            conversation_id=UUID(conversation_key),
            role=role,
            content=content,
            token_estimate=token_estimate,
            tokenizer_name=tokenizer_name,
            message_kind=message_kind,
            archived_at=None,
            usage_json=usage_json,
            created_at=now,
            attachment_links=links,
        )
        self.messages.setdefault(conversation_key, []).append(message)
        conversation = self.conversations.get(conversation_key)
        if conversation is not None:
            conversation.updated_at = now
        return message

    async def list_conversations(self, _session, *, limit=100):
        items = sorted(
            self.conversations.values(),
            key=lambda item: item.updated_at,
            reverse=True,
        )[:limit]
        output = []
        for conversation in items:
            conversation_key = str(conversation.id)
            conversation_messages = self.messages.get(conversation_key, [])
            output.append(
                ConversationListEntry(
                    id=conversation.id,
                    title=conversation.title,
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                    message_count=len(conversation_messages),
                    last_message_at=conversation_messages[-1].created_at
                    if conversation_messages
                    else None,
                )
            )
        return output

    async def get_conversation_messages(self, _session, conversation_id, *, include_archived=True):
        conversation_messages = list(self.messages.get(str(conversation_id), []))
        if include_archived:
            return conversation_messages
        return [item for item in conversation_messages if item.archived_at is None]

    async def build_context_window_for_model(
        self,
        _session,
        *,
        conversation_id,
        max_tokens,
        target_tokens,
        keep_last_turns,
    ):
        _ = (max_tokens, target_tokens, keep_last_turns)
        return await self.get_conversation_messages(
            _session,
            conversation_id,
            include_archived=False,
        )


class _DummySession:
    def __init__(self, store: _MemoryStore):
        self.store = store

    async def get(self, model, key):
        if model is agent_api.Conversation:
            return self.store.conversations.get(str(key))
        if model is agent_api.Attachment:
            return self.store.attachments.get(str(key))
        return None


def _patch_memory_store(monkeypatch):
    store = _MemoryStore()
    monkeypatch.setattr(agent_api, "create_conversation", store.create_conversation)
    monkeypatch.setattr(agent_api, "save_uploaded_attachments", store.save_uploaded_attachments)
    monkeypatch.setattr(
        agent_api,
        "save_user_message_with_attachments",
        store.save_user_message_with_attachments,
    )
    monkeypatch.setattr(agent_api, "save_assistant_message", store.save_assistant_message)
    monkeypatch.setattr(agent_api, "list_conversations", store.list_conversations)
    monkeypatch.setattr(agent_api, "get_conversation_messages", store.get_conversation_messages)
    monkeypatch.setattr(
        agent_api,
        "build_context_window_for_model",
        store.build_context_window_for_model,
    )

    async def _override_db():
        yield _DummySession(store)

    app.dependency_overrides[agent_api.get_db_session] = _override_db
    return store


def _patch_agent(monkeypatch):
    stub = _StubAgent()
    monkeypatch.setattr(agent_api, "get_agent", lambda: stub)
    return stub


def _fake_uploaded_attachment(file_id: str):
    return agent_api.StoredAttachment(
        id=file_id,
        filename="hello.txt",
        content_type="text/plain",
        media_type="text",
        size_bytes=5,
        storage_path="server/storage/uploads/files/hello.txt",
        preview_text="hello",
        extraction_note=None,
        created_at=datetime.now(timezone.utc),
    )


def test_agent_non_stream_response(monkeypatch):
    _patch_memory_store(monkeypatch)
    _patch_agent(monkeypatch)
    client = TestClient(app)

    response = client.post("/api/agent", json={"message": "What time is it?"})

    assert response.status_code == 200
    data = response.json()
    assert data["output_text"] == "It is 2026-02-03T00:00:00Z."
    assert data["tool_calls"][0]["name"] == "utc_time"
    assert data["tool_results"][0]["content"] == "2026-02-03T00:00:00Z"
    assert data["reasoning"][0].startswith("Checking")


def test_upload_send_stream_reload_preserves_messages_and_attachments(monkeypatch):
    store = _patch_memory_store(monkeypatch)
    _patch_agent(monkeypatch)

    async def _fake_store_upload(_upload):
        return _fake_uploaded_attachment(str(uuid4()))

    monkeypatch.setattr(agent_api, "store_uploaded_file", _fake_store_upload)
    client = TestClient(app)

    upload_response = client.post(
        "/api/agent/attachments",
        files=[("files", ("hello.txt", b"hello", "text/plain"))],
    )
    assert upload_response.status_code == 200
    attachment_id = upload_response.json()["files"][0]["id"]
    assert attachment_id in store.attachments

    events = []
    final_payload = None
    with client.stream(
        "POST",
        "/api/agent/stream",
        json={"message": "Stream it", "attachment_ids": [attachment_id]},
    ) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = json.loads(line.removeprefix("data: "))
            events.append(payload["type"])
            if payload["type"] == "final":
                final_payload = payload

    assert "tool_call" in events
    assert "tool_result" in events
    assert "final" in events
    assert final_payload is not None
    assert final_payload["conversation_id"]

    conversation_id = final_payload["conversation_id"]
    reload_response = client.get(f"/api/conversations/{conversation_id}")
    assert reload_response.status_code == 200
    messages = reload_response.json()["messages"]
    assert messages[0]["role"] == "user"
    assert messages[0]["attachments"][0]["id"] == attachment_id
    assert messages[1]["message_kind"] == "tool_call"
    assert messages[2]["message_kind"] == "tool_result"
    assert messages[3]["message_kind"] == "normal"


def test_message_and_attachment_ordering_is_stable(monkeypatch):
    store = _patch_memory_store(monkeypatch)
    _patch_agent(monkeypatch)
    conversation = TestClient(app).post(
        "/api/agent/stream",
        json={"message": "Create order seed"},
    )
    assert conversation.status_code == 200

    conversation_id = next(iter(store.conversations.keys()))
    attachment_a = _fake_uploaded_attachment(str(uuid4()))
    attachment_b = _fake_uploaded_attachment(str(uuid4()))
    attachment_a.filename = "A.txt"
    attachment_b.filename = "B.txt"
    # Save attachment metadata in fixed order.
    import asyncio

    asyncio.run(store.save_uploaded_attachments(None, [attachment_a, attachment_b]))
    asyncio.run(
        store.save_user_message_with_attachments(
            None,
            conversation_id=conversation_id,
            content="Order test",
            attachment_ids=[attachment_a.id, attachment_b.id],
            token_estimate=2,
        )
    )

    client = TestClient(app)
    response = client.get(f"/api/conversations/{conversation_id}")
    assert response.status_code == 200
    payload = response.json()
    last = payload["messages"][-1]
    assert [item["filename"] for item in last["attachments"]] == ["A.txt", "B.txt"]


def test_stream_schema_endpoint():
    client = TestClient(app)
    response = client.get("/api/agent/stream/schema")

    assert response.status_code == 200
    schema = response.json()
    assert "oneOf" in schema or "anyOf" in schema


def test_list_conversations_endpoint(monkeypatch):
    store = _patch_memory_store(monkeypatch)
    _patch_agent(monkeypatch)
    client = TestClient(app)

    stream_response = client.post(
        "/api/agent/stream",
        json={"message": "Create listed conversation"},
    )
    assert stream_response.status_code == 200
    assert store.conversations

    response = client.get("/api/conversations")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert payload[0]["id"] in store.conversations


def teardown_function():
    app.dependency_overrides.clear()
