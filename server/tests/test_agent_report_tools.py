from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from server.features.agent import report_tools
from server.features.reports.types import ReportDetail, ReportSummary


@asynccontextmanager
async def _fake_session_cm():
    yield object()


def _summary(report_id: str) -> ReportSummary:
    now = datetime.now(timezone.utc)
    return ReportSummary(
        id=report_id,
        title="Saved report",
        preview_text="Quick preview",
        source_conversation_id=None,
        enabled_for_agent=True,
        created_at=now,
        updated_at=now,
    )


def _detail(report_id: str) -> ReportDetail:
    base = _summary(report_id)
    return ReportDetail(**base.model_dump(), content="Full report content")


def test_report_tools_expose_expected_contract():
    assert report_tools.list_conversation_reports.name == "list_conversation_reports"
    assert report_tools.get_conversation_report.name == "get_conversation_report"
    assert report_tools.create_conversation_report.name == "create_conversation_report"


@pytest.mark.asyncio
async def test_list_and_get_report_tools_return_payload(monkeypatch):
    report_id = str(uuid4())

    async def _fake_list_reports(_session, *, q, limit, offset, include_disabled):
        assert q == "launch"
        assert limit == 3
        assert offset == 0
        assert include_disabled is False
        return [_summary(report_id)]

    async def _fake_get_report(_session, *, report_id, include_disabled):
        assert include_disabled is False
        return _detail(report_id)

    monkeypatch.setattr(report_tools, "AsyncSessionLocal", _fake_session_cm)
    monkeypatch.setattr(report_tools, "list_reports", _fake_list_reports)
    monkeypatch.setattr(report_tools, "get_report", _fake_get_report)

    listed = await report_tools.list_conversation_reports.ainvoke(
        {"query": "launch", "limit": 3}
    )
    listed_payload = json.loads(listed)
    assert listed_payload["reports"][0]["id"] == report_id

    loaded = await report_tools.get_conversation_report.ainvoke(
        {"report_id": report_id}
    )
    loaded_payload = json.loads(loaded)
    assert loaded_payload["report"]["content"] == "Full report content"


@pytest.mark.asyncio
async def test_create_report_tool_requires_explicit_confirmation(monkeypatch):
    monkeypatch.setattr(report_tools, "AsyncSessionLocal", _fake_session_cm)
    monkeypatch.setattr(
        report_tools,
        "get_request_context",
        lambda: SimpleNamespace(
            latest_user_message="maybe later",
            conversation_id=str(uuid4()),
        ),
    )

    called = {"value": False}

    async def _fake_create_report(*_args, **_kwargs):
        called["value"] = True
        raise AssertionError("Tool should not create a report without confirmation.")

    monkeypatch.setattr(report_tools, "create_report", _fake_create_report)

    output = await report_tools.create_conversation_report.ainvoke(
        {"title": "My report", "content": "Important summary"}
    )
    payload = json.loads(output)
    assert "Missing explicit user confirmation" in payload["error"]
    assert called["value"] is False


@pytest.mark.asyncio
async def test_create_report_tool_uses_context_conversation_id(monkeypatch):
    conversation_id = str(uuid4())
    report_id = str(uuid4())

    monkeypatch.setattr(report_tools, "AsyncSessionLocal", _fake_session_cm)
    monkeypatch.setattr(
        report_tools,
        "get_request_context",
        lambda: SimpleNamespace(
            latest_user_message="yes, save this report",
            conversation_id=conversation_id,
        ),
    )

    async def _fake_create_report(
        _session,
        *,
        title,
        content,
        preview_text,
        enabled_for_agent,
        source_conversation_id,
    ):
        assert title == "Q1 Learnings"
        assert content == "Great results."
        assert preview_text is None
        assert enabled_for_agent is True
        assert source_conversation_id == conversation_id
        return _detail(report_id)

    monkeypatch.setattr(report_tools, "create_report", _fake_create_report)

    output = await report_tools.create_conversation_report.ainvoke(
        {
            "title": "Q1 Learnings",
            "content": "Great results.",
        }
    )
    payload = json.loads(output)
    assert payload["report"]["id"] == report_id
    assert payload["provenance"]["source_conversation_id"] == conversation_id
