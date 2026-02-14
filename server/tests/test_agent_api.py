from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage

from server.db.session import get_db_session

agents_api = importlib.import_module("server.features.agent.api.streaming")
agent_router_api = importlib.import_module("server.features.agent.api.router")
conversations_api = importlib.import_module("server.features.chat.api")
from server.features.chat import ConversationListEntry, ConversationNotFoundError
from server.features.settings.types import ModelSettingsResolved
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
            starred=False,
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
        reasoning_tokens=None,
    ):
        return self._save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            message_kind=message_kind,
            token_estimate=token_estimate,
            tokenizer_name=tokenizer_name,
            usage_json=usage_json,
            reasoning_tokens=reasoning_tokens,
            attachment_ids=[],
        )

    async def save_assistant_message_with_attachments(
        self,
        _session,
        *,
        conversation_id,
        content,
        attachment_ids,
        token_estimate=0,
        tokenizer_name="char4_approx_v1",
        message_kind="tool_result",
        usage_json=None,
        reasoning_tokens=None,
    ):
        return self._save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            message_kind=message_kind,
            token_estimate=token_estimate,
            tokenizer_name=tokenizer_name,
            usage_json=usage_json,
            reasoning_tokens=reasoning_tokens,
            attachment_ids=attachment_ids,
        )

    async def append_message_content(self, _session, *, message_id, content_suffix):
        for items in self.messages.values():
            for message in items:
                if str(message.id) != str(message_id):
                    continue
                message.content = f"{message.content}{content_suffix}"
                return message
        raise ValueError(f"Message '{message_id}' was not found.")

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
        reasoning_tokens=None,
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
            reasoning_tokens=reasoning_tokens,
            created_at=now,
            attachment_links=links,
        )
        self.messages.setdefault(conversation_key, []).append(message)
        conversation = self.conversations.get(conversation_key)
        if conversation is not None:
            conversation.updated_at = now
        return message

    async def list_conversations(self, _session, *, limit=100, cursor=None):
        output = []
        for conversation in self.conversations.values():
            conversation_key = str(conversation.id)
            conversation_messages = self.messages.get(conversation_key, [])
            sort_at = (
                conversation_messages[-1].created_at
                if conversation_messages
                else conversation.updated_at
            )
            output.append(
                ConversationListEntry(
                    id=conversation.id,
                    title=conversation.title,
                    starred=conversation.starred,
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                    message_count=len(conversation_messages),
                    last_message_at=conversation_messages[-1].created_at
                    if conversation_messages
                    else None,
                    sort_at=sort_at,
                )
            )
        output.sort(
            key=lambda item: (
                item.starred,
                item.sort_at,
                item.created_at,
                item.id,
            ),
            reverse=True,
        )

        if cursor is not None:
            filtered: list[ConversationListEntry] = []
            for item in output:
                if item.starred != cursor.starred:
                    should_include = not item.starred and cursor.starred
                elif item.sort_at != cursor.sort_at:
                    should_include = item.sort_at < cursor.sort_at
                elif item.created_at != cursor.created_at:
                    should_include = item.created_at < cursor.created_at
                else:
                    should_include = item.id.int < cursor.id.int
                if should_include:
                    filtered.append(item)
            output = filtered

        return output[: limit + 1]

    async def get_conversation_summary(self, _session, *, conversation_id):
        conversation = self.conversations.get(str(conversation_id))
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation '{conversation_id}' was not found.")
        messages = self.messages.get(str(conversation.id), [])
        return ConversationListEntry(
            id=conversation.id,
            title=conversation.title,
            starred=conversation.starred,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(messages),
            last_message_at=messages[-1].created_at if messages else None,
            sort_at=messages[-1].created_at if messages else conversation.updated_at,
        )

    async def rename_conversation(self, _session, *, conversation_id, title):
        conversation = self.conversations.get(str(conversation_id))
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation '{conversation_id}' was not found.")
        conversation.title = title
        conversation.updated_at = datetime.now(timezone.utc)
        return conversation

    async def set_conversation_starred(self, _session, *, conversation_id, starred):
        conversation = self.conversations.get(str(conversation_id))
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation '{conversation_id}' was not found.")
        conversation.starred = starred
        conversation.updated_at = datetime.now(timezone.utc)
        return conversation

    async def delete_conversation(self, _session, *, conversation_id):
        if str(conversation_id) not in self.conversations:
            raise ConversationNotFoundError(f"Conversation '{conversation_id}' was not found.")
        self.conversations.pop(str(conversation_id), None)
        self.messages.pop(str(conversation_id), None)

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
        if model is agents_api.Conversation:
            return self.store.conversations.get(str(key))
        if model is agents_api.Attachment:
            return self.store.attachments.get(str(key))
        return None


def _patch_memory_store(monkeypatch):
    store = _MemoryStore()
    monkeypatch.setattr(agents_api, "create_conversation", store.create_conversation)
    monkeypatch.setattr(agents_api, "save_uploaded_attachments", store.save_uploaded_attachments)
    monkeypatch.setattr(
        agents_api,
        "save_user_message_with_attachments",
        store.save_user_message_with_attachments,
    )
    monkeypatch.setattr(agents_api, "save_assistant_message", store.save_assistant_message)
    monkeypatch.setattr(
        agents_api,
        "save_assistant_message_with_attachments",
        store.save_assistant_message_with_attachments,
    )
    monkeypatch.setattr(agents_api, "append_message_content", store.append_message_content)
    monkeypatch.setattr(agents_api, "build_context_window_for_model", store.build_context_window_for_model)
    monkeypatch.setattr(conversations_api, "list_conversations", store.list_conversations)
    monkeypatch.setattr(conversations_api, "get_conversation_summary", store.get_conversation_summary)
    monkeypatch.setattr(conversations_api, "get_conversation_messages", store.get_conversation_messages)
    monkeypatch.setattr(conversations_api, "rename_conversation", store.rename_conversation)
    monkeypatch.setattr(conversations_api, "set_conversation_starred", store.set_conversation_starred)
    monkeypatch.setattr(conversations_api, "delete_conversation", store.delete_conversation)
    monkeypatch.setattr(
        conversations_api,
        "build_context_window_for_model",
        store.build_context_window_for_model,
    )

    async def _override_db():
        yield _DummySession(store)

    async def _fake_model_settings(_session):
        return ModelSettingsResolved(
            model_name="gpt-4.1-mini",
            api_key="test-key",
            base_url="",
            temperature=1.0,
            reasoning_effort="medium",
            reasoning_enabled=True,
            source="environment_defaults",
        )

    monkeypatch.setattr(agents_api, "resolve_effective_model_settings", _fake_model_settings)
    monkeypatch.setattr(agent_router_api, "resolve_effective_model_settings", _fake_model_settings)

    app.dependency_overrides[get_db_session] = _override_db
    return store


def _patch_agent(monkeypatch):
    stub = _StubAgent()
    monkeypatch.setattr(agents_api, "get_agent", lambda *_args, **_kwargs: stub)
    return stub


def _fake_uploaded_attachment(file_id: str):
    return agents_api.StoredAttachment(
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


def _payload_message_texts(messages):
    output = []
    for message in messages:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            output.append(content)
        else:
            output.append(json.dumps(content, ensure_ascii=True))
    return output


def test_agent_non_stream_response(monkeypatch):
    _patch_memory_store(monkeypatch)
    _patch_agent(monkeypatch)
    client = TestClient(app)

    response = client.post("/api/agent", json={"message": "What time is it?"})

    assert response.status_code == 200
    data = response.json()
    assert data["output_text"] == "It is 2026-02-03T00:00:00Z."
    assert data["model"] == "gpt-4.1-mini"
    assert data["tool_calls"][0]["name"] == "utc_time"
    assert data["tool_results"][0]["content"] == "2026-02-03T00:00:00Z"
    assert data["reasoning"][0].startswith("Checking")


def test_agent_non_stream_uses_overridden_model_settings(monkeypatch):
    _patch_memory_store(monkeypatch)
    _patch_agent(monkeypatch)

    async def _fake_model_settings(_session):
        return ModelSettingsResolved(
            model_name="openai/gpt-5-mini",
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.7,
            reasoning_effort="high",
            reasoning_enabled=True,
            source="database",
        )

    monkeypatch.setattr(agents_api, "resolve_effective_model_settings", _fake_model_settings)
    monkeypatch.setattr(agent_router_api, "resolve_effective_model_settings", _fake_model_settings)

    client = TestClient(app)
    response = client.post("/api/agent", json={"message": "What time is it?"})

    assert response.status_code == 200
    assert response.json()["model"] == "openai/gpt-5-mini"


def test_upload_send_stream_reload_preserves_messages_and_attachments(monkeypatch):
    store = _patch_memory_store(monkeypatch)
    _patch_agent(monkeypatch)

    async def _fake_store_upload(_upload):
        return _fake_uploaded_attachment(str(uuid4()))

    monkeypatch.setattr(agents_api, "store_uploaded_file", _fake_store_upload)
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


def test_stream_tool_result_artifacts_are_emitted_and_persisted(monkeypatch):
    store = _patch_memory_store(monkeypatch)

    artifact = _fake_uploaded_attachment(str(uuid4()))

    import asyncio

    asyncio.run(store.save_uploaded_attachments(None, [artifact]))

    class _ArtifactStubAgent:
        async def ainvoke(self, payload):
            return {"messages": payload["messages"]}

        async def astream(self, payload, stream_mode=("messages", "updates")):
            tool_call = {
                "id": "call-plot",
                "name": "run_python_code",
                "args": {"code": "print('plot')"},
                "type": "tool_call",
            }
            ai_msg = AIMessage(
                content=[{"type": "text", "text": "Generating a plot."}],
                tool_calls=[tool_call],
                usage_metadata={"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
                response_metadata={"model_name": "gpt-4.1-mini"},
            )
            tool_msg = ToolMessage(
                content=json.dumps(
                    {
                        "status": "succeeded",
                        "summary": "Sandbox execution completed.",
                        "sandbox_reused": True,
                        "artifact_attachment_ids": [artifact.id],
                        "artifacts": [
                            {
                                "id": artifact.id,
                                "filename": artifact.filename,
                                "content_type": artifact.content_type,
                                "media_type": artifact.media_type,
                                "size_bytes": artifact.size_bytes,
                            }
                        ],
                        "input_files": [
                            {
                                "attachment_id": "input-1",
                                "original_filename": "campaign.csv",
                                "sandbox_filename": "01_campaign.csv",
                                "content_type": "text/csv",
                                "input_path": "/workspace/input/01_campaign.csv",
                            }
                        ],
                        "stdout_tail": "ok",
                        "stderr_tail": "",
                    }
                ),
                tool_call_id="call-plot",
            )
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

    monkeypatch.setattr(agents_api, "get_agent", lambda *_args, **_kwargs: _ArtifactStubAgent())
    client = TestClient(app)

    tool_result_payload = None
    final_payload = None
    with client.stream(
        "POST",
        "/api/agent/stream",
        json={"message": "Please run python analysis and plot this"},
    ) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = json.loads(line.removeprefix("data: "))
            if payload["type"] == "tool_result":
                tool_result_payload = payload
            if payload["type"] == "final":
                final_payload = payload

    assert tool_result_payload is not None
    assert tool_result_payload["artifacts"][0]["id"] == artifact.id
    assert tool_result_payload["payload"]["status"] == "succeeded"
    assert tool_result_payload["payload"]["stdout_tail"] == "ok"
    assert tool_result_payload["payload"]["stderr_tail"] == ""
    assert "artifact_attachments:" in tool_result_payload["content"]
    assert "sandbox_reused: true" in tool_result_payload["content"]
    assert "input_files:" in tool_result_payload["content"]
    assert "01_campaign.csv" in tool_result_payload["content"]
    assert final_payload is not None

    conversation_id = final_payload["conversation_id"]
    reload_response = client.get(f"/api/conversations/{conversation_id}")
    assert reload_response.status_code == 200
    messages = reload_response.json()["messages"]
    tool_result_message = next(item for item in messages if item["message_kind"] == "tool_result")
    assert tool_result_message["attachments"][0]["id"] == artifact.id
    assert "artifact_attachments:" in tool_result_message["content"]
    assert "sandbox_reused: true" in tool_result_message["content"]
    assert "input_files:" in tool_result_message["content"]


def test_stream_injects_live_sandbox_status_message(monkeypatch):
    _patch_memory_store(monkeypatch)
    stub = _patch_agent(monkeypatch)

    async def _fake_status(_session, *, conversation_id):
        _ = conversation_id
        return SimpleNamespace(
            alive=True,
            session_id="session-123",
            request_sequence=4,
            reason="alive",
            last_used_at=None,
            available_files=["01_campaign.csv"],
        )

    monkeypatch.setattr(agents_api, "get_conversation_sandbox_status", _fake_status)
    client = TestClient(app)
    response = client.post("/api/agent/stream", json={"message": "hello"})
    assert response.status_code == 200

    assert stub.last_payload is not None
    texts = _payload_message_texts(stub.last_payload["messages"])
    assert any("sandbox_session_alive: true" in text for text in texts)
    assert any("sandbox_status_reason: alive" in text for text in texts)


def test_stream_injects_stale_status_when_ttl_expired(monkeypatch):
    _patch_memory_store(monkeypatch)
    stub = _patch_agent(monkeypatch)

    async def _fake_status(_session, *, conversation_id):
        _ = conversation_id
        return SimpleNamespace(
            alive=False,
            session_id="session-ttl",
            request_sequence=7,
            reason="ttl_expired",
            last_used_at=None,
            available_files=[],
        )

    monkeypatch.setattr(agents_api, "get_conversation_sandbox_status", _fake_status)
    client = TestClient(app)
    response = client.post("/api/agent/stream", json={"message": "hello"})
    assert response.status_code == 200

    assert stub.last_payload is not None
    texts = _payload_message_texts(stub.last_payload["messages"])
    assert any("sandbox_session_alive: false" in text for text in texts)
    assert any("sandbox_status_reason: ttl_expired" in text for text in texts)


def test_stream_injects_status_when_container_missing(monkeypatch):
    _patch_memory_store(monkeypatch)
    stub = _patch_agent(monkeypatch)

    async def _fake_status(_session, *, conversation_id):
        _ = conversation_id
        return SimpleNamespace(
            alive=False,
            session_id="session-dead",
            request_sequence=2,
            reason="container_not_running",
            last_used_at=None,
            available_files=[],
        )

    monkeypatch.setattr(agents_api, "get_conversation_sandbox_status", _fake_status)
    client = TestClient(app)
    response = client.post("/api/agent/stream", json={"message": "hello"})
    assert response.status_code == 200

    assert stub.last_payload is not None
    texts = _payload_message_texts(stub.last_payload["messages"])
    assert any("sandbox_session_alive: false" in text for text in texts)
    assert any("sandbox_status_reason: container_not_running" in text for text in texts)


def test_stream_persists_reasoning_kind_in_interleaved_order(monkeypatch):
    _patch_memory_store(monkeypatch)

    class _InterleavedReasoningStubAgent:
        async def ainvoke(self, payload):
            return {"messages": payload["messages"]}

        async def astream(self, payload, stream_mode=("messages", "updates")):
            tool_call = {
                "id": "call-interleave",
                "name": "utc_time",
                "args": {},
                "type": "tool_call",
            }
            ai_with_tool = AIMessage(
                content=[{"type": "text", "text": "Calling tool."}],
                tool_calls=[tool_call],
                usage_metadata={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                response_metadata={"model_name": "gpt-4.1-mini"},
            )
            tool_msg = ToolMessage(
                content="2026-02-03T00:00:00Z",
                tool_call_id="call-interleave",
            )
            final_msg = AIMessage(
                content=[{"type": "text", "text": "Done."}],
                usage_metadata={
                    "input_tokens": 2,
                    "output_tokens": 3,
                    "total_tokens": 5,
                    "output_token_details": {"reasoning_tokens": 11},
                },
                response_metadata={"model_name": "gpt-4.1-mini"},
            )

            if "messages" in stream_mode and "updates" in stream_mode:
                from langchain_core.messages import AIMessageChunk

                first_reasoning = AIMessageChunk(
                    content=[],
                    additional_kwargs={"reasoning_content": "First reasoning phase. "},
                )
                second_reasoning = AIMessageChunk(
                    content=[],
                    additional_kwargs={"reasoning_content": "Second reasoning phase."},
                )
                final_text = AIMessageChunk(content=[{"type": "text", "text": "Done"}])
                yield ("messages", (first_reasoning, {"langgraph_node": "model"}))
                yield ("updates", {"model": {"messages": [*payload["messages"], ai_with_tool]}})
                yield ("messages", (second_reasoning, {"langgraph_node": "model"}))
                yield ("updates", {"tools": {"messages": [tool_msg]}})
                yield ("messages", (final_text, {"langgraph_node": "model"}))
                yield ("updates", {"model": {"messages": [final_msg]}})
                return

            if "messages" in stream_mode:
                from langchain_core.messages import AIMessageChunk

                yield (
                    "messages",
                    (
                        AIMessageChunk(
                            content=[],
                            additional_kwargs={"reasoning_content": "First reasoning phase. "},
                        ),
                        {"langgraph_node": "model"},
                    ),
                )
                yield ("messages", (AIMessageChunk(content=[{"type": "text", "text": "Done"}]), {"langgraph_node": "model"}))

            if "updates" in stream_mode:
                yield ("updates", {"model": {"messages": [*payload["messages"], ai_with_tool]}})
                yield ("updates", {"tools": {"messages": [tool_msg]}})
                yield ("updates", {"model": {"messages": [final_msg]}})

    monkeypatch.setattr(
        agents_api,
        "get_agent",
        lambda *_args, **_kwargs: _InterleavedReasoningStubAgent(),
    )
    client = TestClient(app)

    final_payload = None
    with client.stream(
        "POST",
        "/api/agent/stream",
        json={"message": "Stream with interleaved reasoning"},
    ) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = json.loads(line.removeprefix("data: "))
            if payload["type"] == "final":
                final_payload = payload

    assert final_payload is not None
    conversation_id = final_payload["conversation_id"]
    reload_response = client.get(f"/api/conversations/{conversation_id}")
    assert reload_response.status_code == 200
    messages = reload_response.json()["messages"]

    assert messages[1]["message_kind"] == "reasoning"
    assert messages[2]["message_kind"] == "tool_call"
    assert messages[3]["message_kind"] == "reasoning"
    assert messages[4]["message_kind"] == "tool_result"
    assert messages[5]["message_kind"] == "normal"
    assert messages[5]["reasoning_tokens"] == 11


def test_stream_emits_sandbox_status_events(monkeypatch):
    _patch_memory_store(monkeypatch)

    class _SandboxStatusStubAgent:
        async def ainvoke(self, payload):
            return {"messages": payload["messages"]}

        async def astream(self, payload, stream_mode=("messages", "updates")):
            from server.features.agent.sandbox.event_bus import emit_sandbox_status

            final_msg = AIMessage(
                content=[{"type": "text", "text": "Done."}],
                usage_metadata={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                response_metadata={"model_name": "gpt-4.1-mini"},
            )
            await emit_sandbox_status(
                run_id="sandbox-run-1",
                stage="executing",
                message="Running pandas analysis.",
            )
            if "messages" in stream_mode:
                from langchain_core.messages import AIMessageChunk

                chunk = AIMessageChunk(content=[{"type": "text", "text": "Done"}])
                yield ("messages", (chunk, {"langgraph_node": "model"}))
            if "updates" in stream_mode:
                yield ("updates", {"model": {"messages": [final_msg]}})

    monkeypatch.setattr(agents_api, "get_agent", lambda *_args, **_kwargs: _SandboxStatusStubAgent())
    client = TestClient(app)

    events = []
    with client.stream(
        "POST",
        "/api/agent/stream",
        json={"message": "Run python plot analysis"},
    ) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = json.loads(line.removeprefix("data: "))
            events.append(payload["type"])

    assert "sandbox_status" in events


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
    rendered = json.dumps(schema)
    assert "sandbox_status" in rendered


def test_reset_sandbox_endpoint(monkeypatch):
    _patch_memory_store(monkeypatch)

    async def _fake_reset(_session, *, conversation_id):
        _ = conversation_id
        return True

    monkeypatch.setattr(agent_router_api, "reset_conversation_sandbox", _fake_reset)
    client = TestClient(app)
    response = client.post(f"/api/agent/conversations/{uuid4()}/sandbox/reset")
    assert response.status_code == 200
    assert response.json() == {"reset": True}


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
    assert len(payload["items"]) >= 1
    assert payload["items"][0]["id"] in store.conversations
    assert payload["items"][0]["starred"] is False
    assert payload["has_more"] is False
    assert payload["next_cursor"] is None


def test_conversation_title_star_delete_endpoints(monkeypatch):
    store = _patch_memory_store(monkeypatch)
    _patch_agent(monkeypatch)
    client = TestClient(app)

    stream_response = client.post(
        "/api/agent/stream",
        json={"message": "Conversation action seed"},
    )
    assert stream_response.status_code == 200
    conversation_id = next(iter(store.conversations.keys()))

    rename_response = client.patch(
        f"/api/conversations/{conversation_id}/title",
        json={"title": "Renamed conversation"},
    )
    assert rename_response.status_code == 200
    assert rename_response.json()["title"] == "Renamed conversation"

    star_response = client.patch(
        f"/api/conversations/{conversation_id}/star",
        json={"starred": True},
    )
    assert star_response.status_code == 200
    assert star_response.json()["starred"] is True

    list_response = client.get("/api/conversations")
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == conversation_id
    assert list_response.json()["items"][0]["starred"] is True

    delete_response = client.delete(f"/api/conversations/{conversation_id}")
    assert delete_response.status_code == 204
    assert conversation_id not in store.conversations


def test_list_conversations_endpoint_supports_cursor_pagination(monkeypatch):
    _patch_memory_store(monkeypatch)
    _patch_agent(monkeypatch)
    client = TestClient(app)

    for index in range(5):
        stream_response = client.post(
            "/api/agent/stream",
            json={"message": f"Pagination seed {index}"},
        )
        assert stream_response.status_code == 200

    first_page = client.get("/api/conversations", params={"limit": 2})
    assert first_page.status_code == 200
    first_payload = first_page.json()
    first_ids = [item["id"] for item in first_payload["items"]]
    assert len(first_ids) == 2
    assert first_payload["has_more"] is True
    assert first_payload["next_cursor"]

    second_page = client.get(
        "/api/conversations",
        params={"limit": 2, "cursor": first_payload["next_cursor"]},
    )
    assert second_page.status_code == 200
    second_payload = second_page.json()
    second_ids = [item["id"] for item in second_payload["items"]]
    assert len(second_ids) == 2
    assert set(first_ids).isdisjoint(second_ids)

    full_response = client.get("/api/conversations", params={"limit": 10})
    assert full_response.status_code == 200
    full_ids = [item["id"] for item in full_response.json()["items"]]
    assert [*first_ids, *second_ids] == full_ids[:4]


def test_list_conversations_endpoint_rejects_invalid_cursor(monkeypatch):
    _patch_memory_store(monkeypatch)
    _patch_agent(monkeypatch)
    client = TestClient(app)

    response = client.get("/api/conversations", params={"cursor": "invalid-cursor", "limit": 2})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid pagination cursor."


def teardown_function():
    app.dependency_overrides.clear()
