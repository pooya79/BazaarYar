from __future__ import annotations

import importlib
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

reports_api = importlib.import_module("server.features.reports.api")
from server.features.reports.errors import ReportNotFoundError
from server.features.reports.types import ReportDetail, ReportSummary
from server.main import app


class _DummySession:
    pass


def _derive_preview(content: str) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= 180:
        return normalized
    return f"{normalized[:179].rstrip()}..."


class _ReportsStore:
    def __init__(self):
        self.reports: dict[str, ReportDetail] = {}

    async def create_report(
        self,
        _session,
        *,
        title,
        content,
        preview_text=None,
        enabled_for_agent=True,
        source_conversation_id=None,
    ):
        now = datetime.now(timezone.utc)
        report = ReportDetail(
            id=str(uuid4()),
            title=title.strip(),
            preview_text=(preview_text.strip() if preview_text and preview_text.strip() else _derive_preview(content)),
            content=content.strip(),
            source_conversation_id=source_conversation_id,
            enabled_for_agent=enabled_for_agent,
            created_at=now,
            updated_at=now,
        )
        self.reports[report.id] = report
        return report

    async def list_reports(
        self,
        _session,
        *,
        q="",
        limit=50,
        offset=0,
        include_disabled=False,
    ):
        items = list(self.reports.values())
        if not include_disabled:
            items = [item for item in items if item.enabled_for_agent]

        clean_q = q.strip().lower()
        if clean_q:
            items = [
                item
                for item in items
                if clean_q in item.title.lower()
                or clean_q in item.preview_text.lower()
                or clean_q in item.content.lower()
            ]

        items.sort(key=lambda item: (item.created_at, item.id), reverse=True)
        page = items[offset : offset + limit]
        return [
            ReportSummary(
                id=item.id,
                title=item.title,
                preview_text=item.preview_text,
                source_conversation_id=item.source_conversation_id,
                enabled_for_agent=item.enabled_for_agent,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in page
        ]

    async def get_report(self, _session, *, report_id, include_disabled=True):
        report = self.reports.get(str(report_id))
        if report is None:
            raise ReportNotFoundError(f"Report '{report_id}' was not found.")
        if not include_disabled and not report.enabled_for_agent:
            raise ReportNotFoundError(f"Report '{report_id}' was not found.")
        return report

    async def update_report(
        self,
        _session,
        *,
        report_id,
        title=None,
        content=None,
        preview_text=None,
        enabled_for_agent=None,
    ):
        report = await self.get_report(_session, report_id=report_id, include_disabled=True)
        if title is not None:
            report.title = title.strip()
        if content is not None:
            report.content = content.strip()
        if preview_text is not None:
            report.preview_text = preview_text.strip()
        if enabled_for_agent is not None:
            report.enabled_for_agent = enabled_for_agent
        report.updated_at = datetime.now(timezone.utc)
        return report

    async def delete_report(self, _session, *, report_id):
        report = self.reports.get(str(report_id))
        if report is None:
            raise ReportNotFoundError(f"Report '{report_id}' was not found.")
        self.reports.pop(str(report_id), None)


def _patch_store(monkeypatch):
    store = _ReportsStore()
    monkeypatch.setattr(reports_api, "create_report", store.create_report)
    monkeypatch.setattr(reports_api, "list_reports", store.list_reports)
    monkeypatch.setattr(reports_api, "get_report", store.get_report)
    monkeypatch.setattr(reports_api, "update_report", store.update_report)
    monkeypatch.setattr(reports_api, "delete_report", store.delete_report)

    async def _override_db():
        yield _DummySession()

    app.dependency_overrides[reports_api.get_db_session] = _override_db
    return store


def test_reports_crud_search_and_toggle_filtering(monkeypatch):
    store = _patch_store(monkeypatch)
    client = TestClient(app)

    first = client.post(
        "/api/reports",
        json={
            "title": "Launch report",
            "content": "Campaign launch details.",
        },
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = client.post(
        "/api/reports",
        json={
            "title": "Retention analysis",
            "content": "Cohort and retention findings.",
            "enabled_for_agent": False,
        },
    )
    assert second.status_code == 201
    second_id = second.json()["id"]

    enabled_only = client.get("/api/reports")
    assert enabled_only.status_code == 200
    enabled_ids = {item["id"] for item in enabled_only.json()}
    assert first_id in enabled_ids
    assert second_id not in enabled_ids

    with_disabled = client.get("/api/reports", params={"include_disabled": True})
    assert with_disabled.status_code == 200
    with_disabled_ids = {item["id"] for item in with_disabled.json()}
    assert first_id in with_disabled_ids
    assert second_id in with_disabled_ids

    search_response = client.get(
        "/api/reports",
        params={"include_disabled": True, "q": "cohort"},
    )
    assert search_response.status_code == 200
    assert [item["id"] for item in search_response.json()] == [second_id]

    patch_response = client.patch(
        f"/api/reports/{second_id}",
        json={"enabled_for_agent": True},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["enabled_for_agent"] is True

    detail_response = client.get(f"/api/reports/{first_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["content"] == "Campaign launch details."

    delete_response = client.delete(f"/api/reports/{first_id}")
    assert delete_response.status_code == 204
    assert first_id not in store.reports

    missing_response = client.get(f"/api/reports/{uuid4()}")
    assert missing_response.status_code == 404
