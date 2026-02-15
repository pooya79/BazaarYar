from __future__ import annotations

import json
import re
from typing import Any

from langchain.tools import tool

from server.db.session import AsyncSessionLocal
from server.features.agent.prompts import (
    CREATE_CONVERSATION_REPORT_TOOL_DESCRIPTION,
    GET_CONVERSATION_REPORT_TOOL_DESCRIPTION,
    LIST_CONVERSATION_REPORTS_TOOL_DESCRIPTION,
)
from server.features.agent.sandbox.event_bus import get_request_context
from server.features.reports import create_report, get_report, list_reports


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True)


_SHORT_CONFIRMATIONS = {
    "yes",
    "y",
    "sure",
    "ok",
    "okay",
    "go ahead",
    "do it",
    "please do",
}


def _is_explicit_save_confirmation(message: str) -> bool:
    normalized = " ".join(message.lower().split())
    if not normalized:
        return False
    if normalized in _SHORT_CONFIRMATIONS:
        return True
    if re.search(
        r"\b(save|archive|store|create)\b.{0,40}\b(report|summary|conversation)\b",
        normalized,
    ):
        return True
    if re.search(
        r"\b(yes|sure|ok|okay|go ahead|please)\b.{0,25}\b(save|archive|store|create)\b",
        normalized,
    ):
        return True
    return False


@tool(description=LIST_CONVERSATION_REPORTS_TOOL_DESCRIPTION)
async def list_conversation_reports(query: str = "", limit: int = 5) -> str:
    safe_limit = max(1, min(limit, 20))
    try:
        async with AsyncSessionLocal() as session:
            rows = await list_reports(
                session,
                q=query,
                limit=safe_limit,
                offset=0,
                include_disabled=False,
            )
        return _dump(
            {
                "reports": [item.model_dump(mode="json") for item in rows],
                "provenance": {
                    "tool": "list_conversation_reports",
                    "query": query,
                    "limit": safe_limit,
                    "enabled_only": True,
                },
            }
        )
    except Exception as exc:
        return _dump(
            {
                "error": str(exc),
                "provenance": {"tool": "list_conversation_reports"},
            }
        )


@tool(description=GET_CONVERSATION_REPORT_TOOL_DESCRIPTION)
async def get_conversation_report(report_id: str) -> str:
    try:
        async with AsyncSessionLocal() as session:
            report = await get_report(
                session,
                report_id=report_id,
                include_disabled=False,
            )
        return _dump(
            {
                "report": report.model_dump(mode="json"),
                "provenance": {
                    "tool": "get_conversation_report",
                    "report_id": report_id,
                    "enabled_only": True,
                },
            }
        )
    except Exception as exc:
        return _dump(
            {
                "error": str(exc),
                "provenance": {
                    "tool": "get_conversation_report",
                    "report_id": report_id,
                },
            }
        )


@tool(description=CREATE_CONVERSATION_REPORT_TOOL_DESCRIPTION)
async def create_conversation_report(
    title: str,
    content: str,
    preview_text: str | None = None,
    enabled_for_agent: bool = True,
) -> str:
    context = get_request_context()
    latest_user_message = context.latest_user_message.strip() if context else ""
    if not _is_explicit_save_confirmation(latest_user_message):
        return _dump(
            {
                "error": (
                    "Missing explicit user confirmation. Ask the user to confirm "
                    "saving the conversation report, then call this tool again."
                ),
                "provenance": {
                    "tool": "create_conversation_report",
                    "confirmed": False,
                },
            }
        )

    try:
        async with AsyncSessionLocal() as session:
            report = await create_report(
                session,
                title=title,
                content=content,
                preview_text=preview_text,
                enabled_for_agent=enabled_for_agent,
                source_conversation_id=context.conversation_id if context else None,
            )
        return _dump(
            {
                "report": report.model_dump(mode="json"),
                "provenance": {
                    "tool": "create_conversation_report",
                    "confirmed": True,
                    "source_conversation_id": (
                        context.conversation_id if context else None
                    ),
                },
            }
        )
    except Exception as exc:
        return _dump(
            {
                "error": str(exc),
                "provenance": {
                    "tool": "create_conversation_report",
                    "confirmed": True,
                },
            }
        )


REPORT_TOOLS = [
    list_conversation_reports,
    get_conversation_report,
    create_conversation_report,
]
