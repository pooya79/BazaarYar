from __future__ import annotations

from typing import Any, Iterable

from langchain_core.messages import AIMessage, BaseMessage

from server.agents.models import openailike_model_spec
from server.agents.runtime import (
    build_agent_runtime,
    extract_trace as extract_trace_base,
    split_openai_like_content,
)

_MODEL_SPEC = openailike_model_spec()
MODEL_NAME = _MODEL_SPEC.name


def build_agent():
    return build_agent_runtime(_MODEL_SPEC.build_model())


_agent_instance = None


def get_agent():
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = build_agent()
    return _agent_instance


def split_ai_content(message: AIMessage) -> tuple[list[str], list[str]]:
    return split_openai_like_content(message)


def extract_trace(messages: Iterable[BaseMessage]) -> dict[str, Any]:
    return extract_trace_base(messages, model_name=MODEL_NAME, split_fn=split_ai_content)
