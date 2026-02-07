from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain.tools import tool

from server.agents.usage import extract_usage

SYSTEM_PROMPT = (
    "You are BazaarYar, an assistant that is concise, practical, and transparent. "
    "When helpful, call tools to retrieve facts or compute results. "
    "Expose tool usage and provide a brief reasoning summary when the user requests it."
)


@tool(description="Add two numbers and return the sum.")
def add_numbers(a: float, b: float) -> str:
    return str(a + b)


@tool(description="Reverse the provided text.")
def reverse_text(text: str) -> str:
    return text[::-1]


@tool(description="Get the current UTC time in ISO-8601 format.")
def utc_time() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


TOOLS = [add_numbers, reverse_text, utc_time]


def build_agent_runtime(model: Any):
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )


def _normalize_content_block(block: Any) -> dict[str, Any] | None:
    if not isinstance(block, dict):
        return None
    if block.get("type") == "non_standard":
        nested = block.get("value")
        if isinstance(nested, dict):
            return nested
    return block


def split_openai_like_content(message: AIMessage) -> tuple[list[str], list[str]]:
    reasoning: list[str] = []
    text: list[str] = []

    content = getattr(message, "content_blocks", None) or message.content
    if isinstance(content, list):
        # OpenAI-compatible responses can return mixed content blocks.
        for raw_block in content:
            block = _normalize_content_block(raw_block)
            if block is None:
                continue
            block_type = block.get("type")
            if block_type in {"thinking", "reasoning", "summary", "reasoning_content"}:
                value = (
                    block.get("thinking")
                    or block.get("reasoning")
                    or block.get("summary")
                    or block.get("reasoning_content")
                )
                if value:
                    reasoning.append(str(value))
            elif block_type in {"text", "output_text"}:
                value = block.get("text") or block.get("output_text")
                if value:
                    text.append(str(value))
    elif isinstance(content, str):
        text.append(content)

    if not reasoning:
        # Some providers stash reasoning summaries outside content blocks.
        extra = getattr(message, "additional_kwargs", None) or {}
        for key in ("reasoning", "reasoning_summary", "summary", "reasoning_content"):
            value = extra.get(key)
            if value:
                reasoning.append(str(value))
                break

    if not reasoning:
        response_meta = getattr(message, "response_metadata", None) or {}
        if isinstance(response_meta, dict) and response_meta.get("reasoning_content"):
            reasoning.append(str(response_meta["reasoning_content"]))

    # Some SDKs expose the reasoning payload directly on the message.
    direct_reasoning = getattr(message, "reasoning_content", None)
    if direct_reasoning:
        direct_value = str(direct_reasoning)
        if direct_value not in reasoning:
            reasoning.append(direct_value)

    return reasoning, text


def split_gemini_content(message: AIMessage) -> tuple[list[str], list[str]]:
    reasoning: list[str] = []
    text: list[str] = []

    content = getattr(message, "content_blocks", None) or message.content
    if isinstance(content, list):
        # Gemini 3 returns mixed content blocks, so extract thinking vs text explicitly.
        for raw_block in content:
            block = _normalize_content_block(raw_block)
            if block is None:
                continue
            block_type = block.get("type")
            if block_type == "thinking" and block.get("thinking"):
                reasoning.append(str(block["thinking"]))
            elif block_type == "text" and block.get("text"):
                text.append(str(block["text"]))
    elif isinstance(content, str):
        text.append(content)

    if not reasoning:
        # Gemini may also expose reasoning hints via extra kwargs.
        extra = getattr(message, "additional_kwargs", None) or {}
        if extra.get("thinking"):
            reasoning.append(str(extra["thinking"]))

    return reasoning, text


def extract_trace(
    messages: Iterable[BaseMessage],
    *,
    model_name: str,
    split_fn: Callable[[AIMessage], tuple[list[str], list[str]]],
) -> dict[str, Any]:
    message_list = list(messages)
    tool_calls: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    reasoning: list[str] = []

    for message in message_list:
        if isinstance(message, AIMessage):
            if message.tool_calls:
                for call in message.tool_calls:
                    tool_calls.append(
                        {
                            "id": call.get("id"),
                            "name": call.get("name"),
                            "args": call.get("args", {}),
                            "type": call.get("type"),
                        }
                    )
            thought_blocks, _ = split_fn(message)
            reasoning.extend(thought_blocks)
        elif isinstance(message, ToolMessage):
            tool_results.append(
                {
                    "tool_call_id": message.tool_call_id,
                    "content": message.content,
                }
            )

    # We scan from the end to find the final assistant output and its usage metadata.
    final_ai = next(
        (msg for msg in reversed(message_list) if isinstance(msg, AIMessage)),
        None,
    )

    usage = None
    response_meta = None
    final_text = ""
    if final_ai is not None:
        usage = extract_usage(final_ai)
        response_meta = getattr(final_ai, "response_metadata", None)
        _, final_text_parts = split_fn(final_ai)
        final_text = "".join(final_text_parts).strip()

    return {
        "output_text": final_text,
        "reasoning": reasoning,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "usage": usage,
        "response_metadata": response_meta,
        "model": model_name,
    }
