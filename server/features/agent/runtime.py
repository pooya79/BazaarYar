from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain.tools import tool

from server.features.agent.prompts import (
    ADD_NUMBERS_TOOL_DESCRIPTION,
    REVERSE_TEXT_TOOL_DESCRIPTION,
    UTC_TIME_TOOL_DESCRIPTION,
)
from server.features.agent.sandbox import PYTHON_SANDBOX_TOOLS
from server.features.agent.usage import extract_usage
from server.core.config import get_settings


@tool(description=ADD_NUMBERS_TOOL_DESCRIPTION)
def add_numbers(a: float, b: float) -> str:
    return str(a + b)


@tool(description=REVERSE_TEXT_TOOL_DESCRIPTION)
def reverse_text(text: str) -> str:
    return text[::-1]


@tool(description=UTC_TIME_TOOL_DESCRIPTION)
def utc_time() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"

_BASE_TOOLS = [add_numbers, reverse_text, utc_time]


def _build_tools() -> list[Any]:
    settings = get_settings()
    tools = list(_BASE_TOOLS)
    if settings.sandbox_tool_enabled:
        tools.extend(PYTHON_SANDBOX_TOOLS)
    return tools


TOOLS = _build_tools()


def build_agent_runtime(model: Any, *, system_prompt: str):
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=system_prompt,
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
