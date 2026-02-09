from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import ToolMessage


def conversation_title_from_message(message: str | None) -> str | None:
    if not message:
        return None
    normalized = " ".join(message.split())
    if not normalized:
        return None
    return normalized[:80]


def format_meta_block(label: str, payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return f"{label}\n{payload}"
    try:
        return f"{label}\n{json.dumps(payload, ensure_ascii=True, indent=2)}"
    except Exception:
        return f"{label}\n{payload}"


def format_tool_call(event: dict[str, Any]) -> str:
    lines = [f"name: {event.get('name') or 'unknown'}"]
    if event.get("type"):
        lines.append(f"call_type: {event['type']}")
    if event.get("id"):
        lines.append(f"id: {event['id']}")
    args = event.get("args")
    if args:
        lines.append("args:")
        lines.append(json.dumps(args, ensure_ascii=True, indent=2))
    return "\n".join(lines)


def parse_tool_result_payload(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def artifact_attachment_ids(payload: dict[str, Any] | None) -> list[str]:
    if payload is None:
        return []
    raw = payload.get("artifact_attachment_ids")
    if not isinstance(raw, list):
        return []
    output: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            output.append(item.strip())
    return output


def format_tool_result(message: ToolMessage, *, payload: dict[str, Any] | None = None) -> str:
    lines: list[str] = []
    if message.tool_call_id:
        lines.append(f"tool_call_id: {message.tool_call_id}")
    if payload is None:
        lines.append(str(message.content))
        return "\n".join(lines)

    status = payload.get("status")
    summary = payload.get("summary")
    stdout_tail = payload.get("stdout_tail")
    stderr_tail = payload.get("stderr_tail")
    if status:
        lines.append(f"status: {status}")
    if summary:
        lines.append(f"summary: {summary}")
    if stdout_tail:
        lines.append("stdout:")
        lines.append(str(stdout_tail))
    if stderr_tail:
        lines.append("stderr:")
        lines.append(str(stderr_tail))
    if not lines:
        lines.append(str(message.content))
    return "\n".join(lines)
