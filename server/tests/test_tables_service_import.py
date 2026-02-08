from __future__ import annotations

import asyncio
import importlib
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from server.domain.tables.importers import ParsedImportData
from server.domain.tables.types import (
    ImportFormat,
    ImportStartInput,
    RowsBatchResult,
    TableDataType,
)

tables_service = importlib.import_module("server.domain.tables.service")


class _DummySession:
    pass


def test_start_import_returns_enriched_metadata_and_partial_counts(monkeypatch):
    table_id = uuid4()
    attachment_id = uuid4()
    now = datetime.now(timezone.utc)

    settings = SimpleNamespace(
        tables_max_columns=150,
        tables_max_file_size_bytes=10_000_000,
        tables_max_import_rows=50_000,
        tables_max_cell_length=4_000,
    )

    table = SimpleNamespace(
        id=table_id,
        row_count=0,
        columns=[
            SimpleNamespace(
                name="campaign",
                data_type=TableDataType.TEXT.value,
                nullable=False,
                description=None,
                semantic_hint=None,
                constraints_json=None,
                default_json=None,
            ),
            SimpleNamespace(
                name="impressions",
                data_type=TableDataType.INTEGER.value,
                nullable=False,
                description=None,
                semantic_hint=None,
                constraints_json=None,
                default_json=None,
            ),
        ],
    )
    attachment = SimpleNamespace(
        id=attachment_id,
        filename="campaign-report.csv",
        size_bytes=100,
        storage_path="unused",
    )

    job = SimpleNamespace(
        id=uuid4(),
        table_id=table_id,
        status="pending",
        source_filename=attachment.filename,
        source_format=ImportFormat.CSV.value,
        total_rows=0,
        inserted_rows=0,
        updated_rows=0,
        deleted_rows=0,
        error_count=0,
        errors_json=[],
        created_at=now,
        started_at=now,
        finished_at=None,
    )

    monkeypatch.setattr(tables_service, "get_settings", lambda: settings)

    async def _get_table(_session, *, table_id, with_columns=True):
        _ = (table_id, with_columns)
        return table

    async def _get_attachment(_session, *, attachment_id):
        _ = attachment_id
        return attachment

    async def _create_import_job(_session, **kwargs):
        _ = kwargs
        return job

    async def _mark_running(_session, *, job):
        job.status = "running"
        return job

    async def _finish_job(
        _session,
        *,
        job,
        status,
        total_rows,
        inserted_rows,
        updated_rows,
        deleted_rows,
        errors_json,
    ):
        job.status = status.value
        job.total_rows = total_rows
        job.inserted_rows = inserted_rows
        job.updated_rows = updated_rows
        job.deleted_rows = deleted_rows
        job.errors_json = errors_json
        job.error_count = len(errors_json)
        job.finished_at = datetime.now(timezone.utc)
        return job

    async def _mutate_rows(_session, *, table_id, payload, import_job_id=None):
        _ = (table_id, payload, import_job_id)
        return RowsBatchResult(inserted=1, updated=0, deleted=0)

    monkeypatch.setattr(tables_service.repository, "get_table", _get_table)
    monkeypatch.setattr(tables_service.repository, "get_attachment_for_import", _get_attachment)
    monkeypatch.setattr(tables_service.repository, "create_import_job", _create_import_job)
    monkeypatch.setattr(tables_service.repository, "mark_import_job_running", _mark_running)
    monkeypatch.setattr(tables_service.repository, "finish_import_job", _finish_job)
    monkeypatch.setattr(tables_service, "mutate_rows", _mutate_rows)

    parsed = ParsedImportData(
        source_format=ImportFormat.CSV,
        rows=[
            {"campaign": "Spring", "impressions": "1200"},
            {"campaign": "Broken", "impressions": "oops"},
        ],
        dataset_name_suggestion="campaign_report",
        source_columns={"campaign": "Campaign", "impressions": "Impressions"},
    )
    monkeypatch.setattr(tables_service.importers, "parse_attachment", lambda *args, **kwargs: parsed)
    monkeypatch.setattr(
        tables_service.importers,
        "infer_columns",
        lambda *args, **kwargs: [
            {
                "name": "campaign",
                "source_name": "Campaign",
                "data_type": "text",
                "confidence": 1.0,
                "nullable": False,
                "sample_values": ["Spring"],
            },
            {
                "name": "impressions",
                "source_name": "Impressions",
                "data_type": "integer",
                "confidence": 1.0,
                "nullable": False,
                "sample_values": [1200],
            },
        ],
    )
    monkeypatch.setattr(
        tables_service.importers,
        "validate_import_rows",
        lambda *args, **kwargs: (
            [{"campaign": "Spring", "impressions": 1200}],
            [{"row": 2, "error": "Row validation failed."}],
        ),
    )

    response = asyncio.run(
        tables_service.start_import(
            _DummySession(),
            table_id=str(table_id),
            payload=ImportStartInput(
                attachment_id=str(attachment_id),
                source_format=ImportFormat.CSV,
                has_header=True,
            ),
        )
    )

    assert response["status"] == "completed"
    assert response["total_rows"] == 2
    assert response["inserted_rows"] == 1
    assert response["updated_rows"] == 0
    assert response["deleted_rows"] == 0
    assert response["error_count"] == 1
    assert response["provenance"]["dataset_name_suggestion"] == "campaign_report"
    assert response["provenance"]["source_columns"] == {
        "campaign": "Campaign",
        "impressions": "Impressions",
    }
    assert response["inferred_columns"][0]["source_name"] == "Campaign"
