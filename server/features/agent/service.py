from __future__ import annotations

from typing import Any, Iterable

from langchain_core.messages import AIMessage, BaseMessage

from server.agents.openailike_agent import (
    extract_trace as _extract_trace,
    get_agent as _get_agent,
    split_ai_content as _split_ai_content,
)


def get_agent() -> Any:
    return _get_agent()


def split_ai_content(message: AIMessage) -> tuple[list[str], list[str]]:
    return _split_ai_content(message)


def extract_trace(messages: Iterable[BaseMessage]) -> dict[str, Any]:
    return _extract_trace(messages)
