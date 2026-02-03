from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from server.core.config import get_settings
from server.agents.usage import extract_usage
SYSTEM_PROMPT = (
    "You are BazaarYar, an assistant that is concise, practical, and transparent. "
    "When helpful, call tools to retrieve facts or compute results. "
    "Expose tool usage and provide a brief reasoning summary when the user requests it."
)

settings = get_settings()
MODEL_NAME = settings.gemini_model
THINKING_LEVEL = settings.gemini_thinking_level


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


def build_agent():
    model = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        api_key=settings.google_api_key,
        temperature=1.0,
        include_thoughts=True,
        thinking_level=THINKING_LEVEL,
    )
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )


_agent_instance = None


def get_agent():
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = build_agent()
    return _agent_instance


def split_ai_content(message: AIMessage) -> tuple[list[str], list[str]]:
    reasoning: list[str] = []
    text: list[str] = []

    content = getattr(message, "content_blocks", None) or message.content
    if isinstance(content, list):
        # Gemini 3 returns mixed content blocks, so we extract thinking vs text explicitly.
        for block in content:
            if not isinstance(block, dict):
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


def extract_trace(messages: Iterable[BaseMessage]) -> dict[str, Any]:
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
            thought_blocks, text_blocks = split_ai_content(message)
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
        _, final_text_parts = split_ai_content(final_ai)
        final_text = "".join(final_text_parts).strip()

    return {
        "output_text": final_text,
        "reasoning": reasoning,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "usage": usage,
        "response_metadata": response_meta,
        "model": MODEL_NAME,
    }
