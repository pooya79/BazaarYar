from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str = Field(min_length=1)


class AgentRequest(BaseModel):
    message: str | None = None
    history: list[ChatMessage] | None = None
    attachment_ids: list[str] | None = None
    conversation_id: str | None = None


class AgentResponse(BaseModel):
    output_text: str
    reasoning: list[str]
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    usage: dict[str, Any] | None
    response_metadata: dict[str, Any] | None
    model: str


class UploadedAttachment(BaseModel):
    id: str
    filename: str
    content_type: str
    media_type: Literal["image", "pdf", "text", "spreadsheet", "binary"]
    size_bytes: int
    preview_text: str | None
    extraction_note: str | None


class UploadAttachmentsResponse(BaseModel):
    files: list[UploadedAttachment]
