from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from langchain_core.messages import AIMessage, BaseMessage
from sqlalchemy.ext.asyncio import AsyncSession

from server.features.agent.models import openailike_model_spec
from server.features.agent.prompts.system_prompt import build_agent_system_prompt
from server.features.agent.runtime import (
    build_agent_runtime,
    extract_trace as extract_trace_base,
    is_tool_group_enabled,
    resolve_agent_tools,
    split_openai_like_content,
)
from server.features.reports import list_reports
from server.features.settings.types import (
    CompanyProfileResolved,
    ModelSettingsResolved,
    ToolSettingsResolved,
)

_REPORT_TOOL_KEYS = frozenset(
    {
        "list_conversation_reports",
        "get_conversation_report",
        "create_conversation_report",
    }
)
_REPORT_RETRIEVAL_TOOL_KEYS = frozenset(
    {
        "list_conversation_reports",
        "get_conversation_report",
    }
)


@dataclass(frozen=True)
class ConversationReportPromptSummary:
    id: str
    title: str
    preview_text: str


@dataclass(frozen=True)
class ConversationReportPromptContext:
    conversation_report_tools_enabled: bool
    conversation_report_retrieval_enabled: bool
    preloaded_reports: tuple[ConversationReportPromptSummary, ...]


def _is_tool_enabled(tool_key: str, tool_overrides: dict[str, bool]) -> bool:
    return bool(tool_overrides.get(tool_key, True))


def _any_enabled(tool_keys: frozenset[str], tool_overrides: dict[str, bool]) -> bool:
    return any(_is_tool_enabled(tool_key, tool_overrides) for tool_key in tool_keys)


async def resolve_conversation_report_prompt_context(
    session: AsyncSession,
    *,
    tool_settings: ToolSettingsResolved,
) -> ConversationReportPromptContext:
    tool_overrides = dict(tool_settings.tool_overrides or {})
    tools_enabled = _any_enabled(_REPORT_TOOL_KEYS, tool_overrides)
    retrieval_enabled = _any_enabled(_REPORT_RETRIEVAL_TOOL_KEYS, tool_overrides)
    if not retrieval_enabled:
        return ConversationReportPromptContext(
            conversation_report_tools_enabled=tools_enabled,
            conversation_report_retrieval_enabled=False,
            preloaded_reports=tuple(),
        )

    rows = await list_reports(
        session,
        q="",
        limit=5,
        offset=0,
        include_disabled=False,
    )
    return ConversationReportPromptContext(
        conversation_report_tools_enabled=tools_enabled,
        conversation_report_retrieval_enabled=True,
        preloaded_reports=tuple(
            ConversationReportPromptSummary(
                id=item.id,
                title=item.title,
                preview_text=item.preview_text,
            )
            for item in rows
        ),
    )


def build_agent(
    model_settings: ModelSettingsResolved,
    company_profile: CompanyProfileResolved,
    tool_settings: ToolSettingsResolved,
    report_prompt_context: ConversationReportPromptContext | None = None,
) -> Any:
    model_spec = openailike_model_spec(model_settings)
    python_code_enabled = is_tool_group_enabled("code_runner", tool_settings.tool_overrides)
    if report_prompt_context is None:
        report_tools_enabled = False
        report_retrieval_enabled = False
        preloaded_reports: list[dict[str, str]] = []
    else:
        report_tools_enabled = report_prompt_context.conversation_report_tools_enabled
        report_retrieval_enabled = report_prompt_context.conversation_report_retrieval_enabled
        preloaded_reports = [
            {
                "id": item.id,
                "title": item.title,
                "preview_text": item.preview_text,
            }
            for item in report_prompt_context.preloaded_reports
        ]

    system_prompt = build_agent_system_prompt(
        company_name=company_profile.name,
        company_description=company_profile.description,
        company_enabled=company_profile.enabled,
        python_code_enabled=python_code_enabled,
        conversation_report_tools_enabled=report_tools_enabled,
        conversation_report_retrieval_enabled=report_retrieval_enabled,
        conversation_report_prefetched_items=preloaded_reports,
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
