from __future__ import annotations

import json

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage

from server.agents import api as agent_api
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
            response_metadata={"model_name": "gemini-3-pro-preview"},
        )
        tool_msg = ToolMessage(content="2026-02-03T00:00:00Z", tool_call_id="call-1")
        final_msg = AIMessage(
            content=[{"type": "text", "text": "It is 2026-02-03T00:00:00Z."}],
            usage_metadata={"input_tokens": 2, "output_tokens": 5, "total_tokens": 7},
            response_metadata={"model_name": "gemini-3-pro-preview"},
        )
        return {"messages": [*payload["messages"], ai_msg, tool_msg, final_msg]}

    async def astream(self, payload, stream_mode=("messages", "updates")):
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
            response_metadata={"model_name": "gemini-3-pro-preview"},
        )
        tool_msg = ToolMessage(content="2026-02-03T00:00:00Z", tool_call_id="call-1")
        final_msg = AIMessage(
            content=[{"type": "text", "text": "Done."}],
            usage_metadata={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            response_metadata={"model_name": "gemini-3-pro-preview"},
        )
        if "messages" in stream_mode:
            from langchain_core.messages import AIMessageChunk

            chunk = AIMessageChunk(content=[{"type": "text", "text": "Done"}])
            yield ("messages", (chunk, {"langgraph_node": "model"}))
        if "updates" in stream_mode:
            yield ("updates", {"model": {"messages": [*payload["messages"], ai_msg]}})
            yield ("updates", {"tools": {"messages": [tool_msg]}})
            yield ("updates", {"model": {"messages": [final_msg]}})


def _patch_agent(monkeypatch):
    # Avoid hitting the real Gemini API during tests.
    stub = _StubAgent()
    monkeypatch.setattr(agent_api, "get_agent", lambda: stub)
    return stub


def test_agent_non_stream_response(monkeypatch):
    _patch_agent(monkeypatch)
    client = TestClient(app)

    response = client.post("/api/agent", json={"message": "What time is it?"})

    assert response.status_code == 200
    data = response.json()
    assert data["output_text"] == "It is 2026-02-03T00:00:00Z."
    assert data["tool_calls"][0]["name"] == "utc_time"
    assert data["tool_results"][0]["content"] == "2026-02-03T00:00:00Z"
    assert data["reasoning"][0].startswith("Checking")


def test_agent_stream_sse(monkeypatch):
    _patch_agent(monkeypatch)
    client = TestClient(app)

    events = []
    with client.stream("POST", "/api/agent/stream", json={"message": "Stream it"}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        for line in response.iter_lines():
            if not line:
                continue
            if line.startswith("data: "):
                payload = json.loads(line.removeprefix("data: "))
                events.append(payload["type"])

    assert "tool_call" in events
    assert "tool_result" in events
    assert "text_delta" in events
    assert "final" in events


def test_stream_schema_endpoint():
    client = TestClient(app)
    response = client.get("/api/agent/stream/schema")

    assert response.status_code == 200
    schema = response.json()
    assert "oneOf" in schema or "anyOf" in schema


def test_agent_request_with_attachment_ids(monkeypatch):
    stub = _patch_agent(monkeypatch)
    monkeypatch.setattr(
        agent_api,
        "build_attachment_message_parts",
        lambda attachment_ids: (
            f"Attachment ids: {', '.join(attachment_ids)}",
            [
                {
                    "type": "image",
                    "base64": "abcd",
                    "mime_type": "image/png",
                }
            ],
        ),
    )
    client = TestClient(app)

    response = client.post(
        "/api/agent",
        json={
            "message": "Summarize this file",
            "attachment_ids": ["file-123"],
        },
    )

    assert response.status_code == 200
    assert stub.last_payload is not None
    final_user_message = stub.last_payload["messages"][-1]
    assert isinstance(final_user_message.content, list)
    assert final_user_message.content[0]["type"] == "text"
    assert "Attached file context" in final_user_message.content[1]["text"]
    assert "Attachment ids: file-123" in final_user_message.content[1]["text"]
    assert final_user_message.content[2]["type"] == "image"


def test_upload_attachments_endpoint(monkeypatch):
    async def _fake_store(upload):
        return agent_api.UploadedAttachment(
            id="file-1",
            filename=upload.filename or "unknown.txt",
            content_type=upload.content_type or "text/plain",
            media_type="text",
            size_bytes=5,
            preview_text="hello",
            extraction_note=None,
        )

    monkeypatch.setattr(agent_api, "store_uploaded_file", _fake_store)
    client = TestClient(app)
    response = client.post(
        "/api/agent/attachments",
        files=[("files", ("hello.txt", b"hello", "text/plain"))],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["files"][0]["id"] == "file-1"
    assert payload["files"][0]["filename"] == "hello.txt"
