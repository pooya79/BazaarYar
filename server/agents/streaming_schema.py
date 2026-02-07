from __future__ import annotations

import json
from typing import Any, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter


class TextDeltaEvent(BaseModel):
    type: Literal["text_delta"] = "text_delta"
    content: str


class ReasoningDeltaEvent(BaseModel):
    type: Literal["reasoning_delta"] = "reasoning_delta"
    content: str


class ToolCallDeltaEvent(BaseModel):
    type: Literal["tool_call_delta"] = "tool_call_delta"
    id: str | None = None
    name: str | None = None
    args: str | None = None
    index: int | None = None


class ToolCallEvent(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    id: str | None = None
    name: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    call_type: str | None = None


class ToolResultEvent(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_call_id: str | None = None
    content: str


class FinalEvent(BaseModel):
    type: Literal["final"] = "final"
    output_text: str
    usage: dict[str, Any] | None = None
    response_metadata: dict[str, Any] | None = None
    conversation_id: str | None = None


StreamEvent = Union[
    TextDeltaEvent,
    ReasoningDeltaEvent,
    ToolCallDeltaEvent,
    ToolCallEvent,
    ToolResultEvent,
    FinalEvent,
]


_STREAM_EVENT_ADAPTER = TypeAdapter(StreamEvent)


def stream_event_schema() -> dict[str, Any]:
    return _STREAM_EVENT_ADAPTER.json_schema()


def encode_sse(event: StreamEvent) -> str:
    payload = event.model_dump()
    event_name = payload["type"]
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=True)}\n\n"
