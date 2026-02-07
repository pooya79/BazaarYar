from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from pydantic import BaseModel, Field
from .attachments import build_attachment_message_parts, store_uploaded_file
from .openailike_agent import extract_trace, get_agent, split_ai_content
from .usage import extract_usage
from .streaming_schema import (
    FinalEvent,
    ReasoningDeltaEvent,
    TextDeltaEvent,
    ToolCallDeltaEvent,
    ToolCallEvent,
    ToolResultEvent,
    encode_sse,
    stream_event_schema,
)

router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str = Field(min_length=1)


class AgentRequest(BaseModel):
    message: str | None = None
    history: list[ChatMessage] | None = None
    attachment_ids: list[str] | None = None


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


def _build_messages(payload: AgentRequest) -> list[Any]:
    messages: list[Any] = []
    if payload.history:
        for item in payload.history:
            if item.role == "assistant":
                messages.append(AIMessage(content=item.content))
            else:
                messages.append(HumanMessage(content=item.content))

    user_message = (payload.message or "").strip()
    attachment_ids = [item.strip() for item in (payload.attachment_ids or []) if item.strip()]
    attachment_context = ""
    attachment_blocks: list[dict[str, Any]] = []
    if attachment_ids:
        attachment_context, attachment_blocks = build_attachment_message_parts(attachment_ids)

    if user_message or attachment_context or attachment_blocks:
        if attachment_blocks:
            content: list[dict[str, Any]] = []
            if user_message:
                content.append({"type": "text", "text": user_message})
            if attachment_context:
                content.append(
                    {
                        "type": "text",
                        "text": (
                            "Attached file context:\n"
                            f"{attachment_context}\n\n"
                            "Use extracted content when relevant and call out uncertainty if extraction is incomplete."
                        ),
                    }
                )
            content.extend(attachment_blocks)
            messages.append(HumanMessage(content=content))
        else:
            content_parts: list[str] = []
            if user_message:
                content_parts.append(user_message)
            if attachment_context:
                content_parts.append(
                    "Attached file context:\n"
                    f"{attachment_context}\n\n"
                    "Use extracted content when relevant and call out uncertainty if extraction is incomplete."
                )
            messages.append(HumanMessage(content="\n\n".join(content_parts)))
    return messages


@router.get("/stream/schema")
async def stream_schema() -> dict[str, Any]:
    return stream_event_schema()


@router.post("/attachments", response_model=UploadAttachmentsResponse)
async def upload_attachments(
    files: list[UploadFile] = File(...),
) -> UploadAttachmentsResponse:
    if not files:
        raise HTTPException(status_code=400, detail="Provide at least one file.")

    uploaded: list[UploadedAttachment] = []
    for file in files:
        stored = await store_uploaded_file(file)
        uploaded.append(
            UploadedAttachment(
                id=stored.id,
                filename=stored.filename,
                content_type=stored.content_type,
                media_type=stored.media_type,
                size_bytes=stored.size_bytes,
                preview_text=stored.preview_text,
                extraction_note=stored.extraction_note,
            )
        )
    return UploadAttachmentsResponse(files=uploaded)


@router.post("", response_model=AgentResponse)
async def run_agent(payload: AgentRequest) -> AgentResponse:
    messages = _build_messages(payload)
    if not messages:
        raise HTTPException(status_code=400, detail="Provide message or history.")
    agent = get_agent()
    result = await agent.ainvoke({"messages": messages})
    trace = extract_trace(result["messages"])
    return AgentResponse(**trace)


@router.post("/stream")
async def stream_agent(payload: AgentRequest) -> StreamingResponse:
    messages = _build_messages(payload)
    if not messages:
        raise HTTPException(status_code=400, detail="Provide message or history.")

    async def _event_stream():
        agent = get_agent()
        final_ai: AIMessage | None = None

        async for stream_mode, data in agent.astream(
            {"messages": messages},
            stream_mode=["messages", "updates"],
        ):
            if stream_mode == "messages":
                token, metadata = data
                if isinstance(token, AIMessageChunk):
                    extra = getattr(token, "additional_kwargs", None) or {}
                    reasoning_chunk = getattr(token, "reasoning_content", None) or extra.get(
                        "reasoning_content"
                    )
                    if reasoning_chunk:
                        yield encode_sse(
                            ReasoningDeltaEvent(content=str(reasoning_chunk))
                        )
                    for chunk in token.tool_call_chunks:
                        yield encode_sse(
                            ToolCallDeltaEvent(
                                id=chunk.get("id"),
                                name=chunk.get("name"),
                                args=chunk.get("args"),
                                index=chunk.get("index"),
                            )
                        )
                    content_blocks = getattr(token, "content_blocks", None) or token.content
                    if isinstance(content_blocks, list):
                        for raw_block in content_blocks:
                            if not isinstance(raw_block, dict):
                                continue
                            block = raw_block
                            if raw_block.get("type") == "non_standard":
                                nested = raw_block.get("value")
                                if isinstance(nested, dict):
                                    block = nested
                            block_type = block.get("type")
                            if block_type in {"thinking", "reasoning", "summary"}:
                                value = (
                                    block.get("thinking")
                                    or block.get("reasoning")
                                    or block.get("summary")
                                )
                                if value:
                                    yield encode_sse(
                                        ReasoningDeltaEvent(content=str(value))
                                    )
                            if block_type in {"text", "output_text"}:
                                value = block.get("text") or block.get("output_text")
                                if value:
                                    yield encode_sse(TextDeltaEvent(content=str(value)))
                    elif isinstance(content_blocks, str) and content_blocks:
                        yield encode_sse(TextDeltaEvent(content=content_blocks))
            elif stream_mode == "updates":
                for _, update in data.items():
                    msg_list = update.get("messages", [])
                    if not msg_list:
                        continue
                    msg = msg_list[-1]
                    if isinstance(msg, AIMessage):
                        if msg.tool_calls:
                            for call in msg.tool_calls:
                                yield encode_sse(
                                    ToolCallEvent(
                                        id=call.get("id"),
                                        name=call.get("name"),
                                        args=call.get("args", {}),
                                        call_type=call.get("type"),
                                    )
                                )
                        final_ai = msg
                    elif isinstance(msg, ToolMessage):
                        yield encode_sse(
                            ToolResultEvent(
                                tool_call_id=msg.tool_call_id,
                                content=msg.content,
                            )
                        )

        if final_ai is not None:
            usage = extract_usage(final_ai)
            response_meta = getattr(final_ai, "response_metadata", None)
            _, final_text_parts = split_ai_content(final_ai)
            final_text = "".join(final_text_parts).strip()
            yield encode_sse(
                FinalEvent(
                    output_text=final_text,
                    usage=usage,
                    response_metadata=response_meta,
                )
            )

    return StreamingResponse(_event_stream(), media_type="text/event-stream")
