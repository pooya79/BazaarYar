from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain.tools import tool

from server.features.agent.prompts import (
    ADD_NUMBERS_TOOL_DESCRIPTION,
    REVERSE_TEXT_TOOL_DESCRIPTION,
    UTC_TIME_TOOL_DESCRIPTION,
)
from server.features.agent.report_tools import REPORT_TOOLS
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

_BASE_TOOLS = (add_numbers, reverse_text, utc_time)


@dataclass(frozen=True)
class ToolRegistryEntry:
    key: str
    group_key: str
    group_label: str
    tool_label: str
    description: str
    default_enabled: bool
    tool: Any
    availability: Callable[[Any], tuple[bool, str | None]]


@dataclass(frozen=True)
class ResolvedTool:
    key: str
    label: str
    description: str
    default_enabled: bool
    available: bool
    unavailable_reason: str | None
    enabled: bool
    tool: Any


@dataclass(frozen=True)
class ResolvedToolGroup:
    key: str
    label: str
    enabled: bool
    tools: tuple[ResolvedTool, ...]


def _always_available(_settings: Any) -> tuple[bool, str | None]:
    return True, None


def _sandbox_availability(settings: Any) -> tuple[bool, str | None]:
    if settings.sandbox_tool_enabled:
        return True, None
    return False, "Code runner is disabled by server configuration."


def _tool_label_from_key(key: str) -> str:
    return key.replace("_", " ").strip().title()


def _tool_description(tool_obj: Any) -> str:
    description = getattr(tool_obj, "description", "")
    if not isinstance(description, str):
        return ""
    return description.strip()


def _tool_key(tool_obj: Any) -> str:
    name = getattr(tool_obj, "name", "")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return _tool_label_from_key(str(tool_obj))


def _build_registry() -> tuple[ToolRegistryEntry, ...]:
    utility_tool_labels = {
        "add_numbers": "Add Numbers",
        "reverse_text": "Reverse Text",
        "utc_time": "UTC Time",
    }

    entries: list[ToolRegistryEntry] = []
    seen_keys: set[str] = set()

    for tool_obj in _BASE_TOOLS:
        key = _tool_key(tool_obj)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        entries.append(
            ToolRegistryEntry(
                key=key,
                group_key="basic_tools",
                group_label="Basic tools",
                tool_label=utility_tool_labels.get(key, _tool_label_from_key(key)),
                description=_tool_description(tool_obj),
                default_enabled=True,
                tool=tool_obj,
                availability=_always_available,
            )
        )

    for tool_obj in REPORT_TOOLS:
        key = _tool_key(tool_obj)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        entries.append(
            ToolRegistryEntry(
                key=key,
                group_key="conversation_tools",
                group_label="Conversation tools",
                tool_label=_tool_label_from_key(key),
                description=_tool_description(tool_obj),
                default_enabled=True,
                tool=tool_obj,
                availability=_always_available,
            )
        )

    for tool_obj in PYTHON_SANDBOX_TOOLS:
        key = _tool_key(tool_obj)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        entries.append(
            ToolRegistryEntry(
                key=key,
                group_key="code_runner",
                group_label="Code runner",
                tool_label=_tool_label_from_key(key),
                description=_tool_description(tool_obj),
                default_enabled=True,
                tool=tool_obj,
                availability=_sandbox_availability,
            )
        )

    return tuple(entries)


TOOL_REGISTRY = _build_registry()


def tool_registry_keys() -> set[str]:
    return {entry.key for entry in TOOL_REGISTRY}


def tool_default_enabled_map() -> dict[str, bool]:
    return {entry.key: entry.default_enabled for entry in TOOL_REGISTRY}


def resolve_tool_groups(
    tool_overrides: Mapping[str, bool] | None = None,
) -> tuple[ResolvedToolGroup, ...]:
    settings = get_settings()
    normalized_overrides = dict(tool_overrides or {})
    grouped: dict[str, list[ResolvedTool]] = {}
    group_labels: dict[str, str] = {}
    group_order: list[str] = []

    for entry in TOOL_REGISTRY:
        if entry.group_key not in grouped:
            grouped[entry.group_key] = []
            group_labels[entry.group_key] = entry.group_label
            group_order.append(entry.group_key)

        available, unavailable_reason = entry.availability(settings)
        requested_enabled = normalized_overrides.get(entry.key, entry.default_enabled)
        enabled = bool(requested_enabled) and available

        grouped[entry.group_key].append(
            ResolvedTool(
                key=entry.key,
                label=entry.tool_label,
                description=entry.description,
                default_enabled=entry.default_enabled,
                available=available,
                unavailable_reason=unavailable_reason,
                enabled=enabled,
                tool=entry.tool,
            )
        )

    result: list[ResolvedToolGroup] = []
    for group_key in group_order:
        tools = tuple(grouped[group_key])
        result.append(
            ResolvedToolGroup(
                key=group_key,
                label=group_labels[group_key],
                enabled=any(tool.enabled for tool in tools),
                tools=tools,
            )
        )
    return tuple(result)


def resolve_agent_tools(tool_overrides: Mapping[str, bool] | None = None) -> list[Any]:
    tools: list[Any] = []
    for group in resolve_tool_groups(tool_overrides):
        for resolved in group.tools:
            if resolved.enabled:
                tools.append(resolved.tool)
    return tools


def is_tool_group_enabled(
    group_key: str,
    tool_overrides: Mapping[str, bool] | None = None,
) -> bool:
    for group in resolve_tool_groups(tool_overrides):
        if group.key == group_key:
            return group.enabled
    return False


def build_agent_runtime(model: Any, *, system_prompt: str, tools: list[Any]):
    return create_agent(
        model=model,
        tools=tools,
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
