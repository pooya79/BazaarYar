from __future__ import annotations

import json

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage

from server.agents import api as agent_api
from server.main import app


class _StubAgent:
    async def ainvoke(self, payload):
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
    monkeypatch.setattr(agent_api, "get_agent", lambda: _StubAgent())


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
