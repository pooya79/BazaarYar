from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from server.features.reports import service as reports_service
from server.features.reports.errors import ReportValidationError


class _DummySession:
    pass


def _report_row(
    *,
    title: str = "Title",
    preview_text: str = "Preview",
    content: str = "Content",
    enabled_for_agent: bool = True,
):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        title=title,
        preview_text=preview_text,
        content=content,
        source_conversation_id=None,
        enabled_for_agent=enabled_for_agent,
        created_at=now,
        updated_at=now,
    )


def test_create_report_auto_generates_preview_and_enforces_length(monkeypatch):
    captured: dict[str, object] = {}

    async def _fake_create_report(
        _session,
        *,
        title,
        preview_text,
        content,
        source_conversation_id,
        enabled_for_agent,
    ):
        captured["title"] = title
        captured["preview_text"] = preview_text
        captured["content"] = content
        captured["source_conversation_id"] = source_conversation_id
        captured["enabled_for_agent"] = enabled_for_agent
        return _report_row(
            title=title,
            preview_text=preview_text,
            content=content,
            enabled_for_agent=enabled_for_agent,
        )

    monkeypatch.setattr(reports_service.repo, "create_report", _fake_create_report)

    long_content = " ".join(["growth"] * 80)
    result = asyncio.run(
        reports_service.create_report(
            _DummySession(),
            title="  Q1 Summary  ",
            content=long_content,
            preview_text=None,
        )
    )

    assert captured["title"] == "Q1 Summary"
    assert isinstance(captured["preview_text"], str)
    assert len(captured["preview_text"]) <= 180
    assert result.preview_text == captured["preview_text"]


def test_create_report_sanitizes_text_inputs(monkeypatch):
    captured: dict[str, object] = {}

    async def _fake_create_report(
        _session,
        *,
        title,
        preview_text,
        content,
        source_conversation_id,
        enabled_for_agent,
    ):
        captured["title"] = title
        captured["preview_text"] = preview_text
        captured["content"] = content
        captured["source_conversation_id"] = source_conversation_id
        captured["enabled_for_agent"] = enabled_for_agent
        return _report_row(
            title=title,
            preview_text=preview_text,
            content=content,
            enabled_for_agent=enabled_for_agent,
        )

    monkeypatch.setattr(reports_service.repo, "create_report", _fake_create_report)

    result = asyncio.run(
        reports_service.create_report(
            _DummySession(),
            title="  Ti\x00tle\ud800  ",
            content="  body\r\nline\x00\ud800  ",
            preview_text="  pre\x00\ud800\rline  ",
        )
    )

    assert captured["title"] == "Title\ufffd"
    assert captured["content"] == "body\nline\ufffd"
    assert captured["preview_text"] == "pre\ufffd\nline"
    assert result.title == "Title\ufffd"
    assert result.content == "body\nline\ufffd"
    assert result.preview_text == "pre\ufffd\nline"


def test_create_report_validates_required_fields_and_limits():
    with pytest.raises(ReportValidationError):
        asyncio.run(
            reports_service.create_report(
                _DummySession(),
                title="",
                content="ok",
            )
        )

    with pytest.raises(ReportValidationError):
        asyncio.run(
            reports_service.create_report(
                _DummySession(),
                title="Valid",
                content="",
            )
        )

    with pytest.raises(ReportValidationError):
        asyncio.run(
            reports_service.create_report(
                _DummySession(),
                title="x" * 256,
                content="ok",
            )
        )


def test_update_report_keeps_created_at_immutable(monkeypatch):
    existing = _report_row(
        title="Old",
        preview_text="Old preview",
        content="Old content",
        enabled_for_agent=True,
    )
    created_at = existing.created_at

    async def _fake_get_report(_session, *, report_id, include_disabled):
        _ = report_id
        assert include_disabled is True
        return existing

    async def _fake_update_report(
        _session,
        *,
        report,
        title=None,
        preview_text=None,
        content=None,
        enabled_for_agent=None,
    ):
        if title is not None:
            report.title = title
        if preview_text is not None:
            report.preview_text = preview_text
        if content is not None:
            report.content = content
        if enabled_for_agent is not None:
            report.enabled_for_agent = enabled_for_agent
        report.updated_at = datetime.now(timezone.utc)
        return report

    monkeypatch.setattr(reports_service.repo, "get_report", _fake_get_report)
    monkeypatch.setattr(reports_service.repo, "update_report", _fake_update_report)

    result = asyncio.run(
        reports_service.update_report(
            _DummySession(),
            report_id=str(existing.id),
            title="New",
        )
    )

    assert result.title == "New"
    assert result.created_at == created_at


def test_update_report_sanitizes_text_inputs(monkeypatch):
    existing = _report_row(
        title="Old",
        preview_text="Old preview",
        content="Old content",
        enabled_for_agent=True,
    )

    async def _fake_get_report(_session, *, report_id, include_disabled):
        _ = (report_id, include_disabled)
        return existing

    async def _fake_update_report(
        _session,
        *,
        report,
        title=None,
        preview_text=None,
        content=None,
        enabled_for_agent=None,
    ):
        if title is not None:
            report.title = title
        if preview_text is not None:
            report.preview_text = preview_text
        if content is not None:
            report.content = content
        if enabled_for_agent is not None:
            report.enabled_for_agent = enabled_for_agent
        report.updated_at = datetime.now(timezone.utc)
        return report

    monkeypatch.setattr(reports_service.repo, "get_report", _fake_get_report)
    monkeypatch.setattr(reports_service.repo, "update_report", _fake_update_report)

    result = asyncio.run(
        reports_service.update_report(
            _DummySession(),
            report_id=str(existing.id),
            title="  Ti\x00tle\ud800  ",
            content="  body\r\nline\x00\ud800  ",
            preview_text="  pre\x00\ud800\rline  ",
        )
    )

    assert result.title == "Title\ufffd"
    assert result.content == "body\nline\ufffd"
    assert result.preview_text == "pre\ufffd\nline"
