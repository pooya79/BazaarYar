from __future__ import annotations

from typing import Any, Iterable

from langchain_core.messages import AIMessage, BaseMessage

from server.features.agent.models import openailike_model_spec
from server.features.agent.prompts.system_prompt import build_agent_system_prompt
from server.features.agent.runtime import (
    build_agent_runtime,
    extract_trace as extract_trace_base,
    is_tool_group_enabled,
    resolve_agent_tools,
    split_openai_like_content,
)
from server.features.settings.types import (
    CompanyProfileResolved,
    ModelSettingsResolved,
    ToolSettingsResolved,
)


def build_agent(
    model_settings: ModelSettingsResolved,
    company_profile: CompanyProfileResolved,
    tool_settings: ToolSettingsResolved,
) -> Any:
    model_spec = openailike_model_spec(model_settings)
    python_code_enabled = is_tool_group_enabled("code_runner", tool_settings.tool_overrides)
    system_prompt = build_agent_system_prompt(
        company_name=company_profile.name,
        company_description=company_profile.description,
        company_enabled=company_profile.enabled,
        python_code_enabled=python_code_enabled,
    )
    tools = resolve_agent_tools(tool_settings.tool_overrides)
    return build_agent_runtime(
        model_spec.build_model(),
        system_prompt=system_prompt,
        tools=tools,
    )


def split_ai_content(message: AIMessage) -> tuple[list[str], list[str]]:
    return split_openai_like_content(message)


def extract_trace(messages: Iterable[BaseMessage], *, model_name: str) -> dict[str, Any]:
    return extract_trace_base(messages, model_name=model_name, split_fn=split_ai_content)
