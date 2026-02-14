from __future__ import annotations

from typing import Any, Iterable

from langchain_core.messages import AIMessage, BaseMessage

from server.features.agent.models import openailike_model_spec
from server.features.agent.runtime import (
    build_agent_runtime,
    extract_trace as extract_trace_base,
    split_openai_like_content,
)
from server.features.settings.types import ModelSettingsResolved


def build_agent(model_settings: ModelSettingsResolved) -> Any:
    model_spec = openailike_model_spec(model_settings)
    return build_agent_runtime(model_spec.build_model())


def split_ai_content(message: AIMessage) -> tuple[list[str], list[str]]:
    return split_openai_like_content(message)


def extract_trace(messages: Iterable[BaseMessage], *, model_name: str) -> dict[str, Any]:
    return extract_trace_base(messages, model_name=model_name, split_fn=split_ai_content)
