from __future__ import annotations

import asyncio
import importlib
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from server.features.tables.importers import ParsedImportData
from server.features.tables.types import (
    ImportFormat,
    ImportStartInput,
    ReferenceTableCreateInput,
    ReferenceTableColumnInput,
    RowsBatchInput,
    RowsBatchResult,
    RowUpsert,
    SourceActor,
    TableDataType,
)

tables_service = importlib.import_module("server.features.tables.service")


class _DummySession:
    pass


def test_create_table_sanitizes_metadata_and_column_text(monkeypatch):
    settings = SimpleNamespace(
        tables_max_columns=150,
        tables_max_cell_length=4_000,
    )
    monkeypatch.setattr(tables_service, "get_settings", lambda: settings)

    async def _get_table_by_name(_session, *, name, with_columns=False):
        _ = (name, with_columns)
        return None

    captured: dict[str, object] = {}

    async def _create_table_with_columns(_session, *, name, title, description, columns):
        captured["name"] = name
        captured["title"] = title
        captured["description"] = description
        captured["columns"] = columns
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=uuid4(),
            name=name,
            title=title,
            description=description,
            row_count=0,
            created_at=now,
            updated_at=now,
            columns=[
                SimpleNamespace(
                    id=uuid4(),
                    name=item["name"],
                    position=index,
                    data_type=item["data_type"],
                    nullable=item["nullable"],
                    description=item.get("description"),
                    semantic_hint=item.get("semantic_hint"),
                    constraints_json=item.get("constraints_json"),
                    default_json=item.get("default_value"),
                )
                for index, item in enumerate(columns)
            ],
        )

    monkeypatch.setattr(tables_service.repo, "get_table_by_name", _get_table_by_name)
    monkeypatch.setattr(tables_service.repo, "create_table_with_columns", _create_table_with_columns)

    result = asyncio.run(
        tables_service.create_table(
            _DummySession(),
            payload=ReferenceTableCreateInput(
                name="campaign_metrics",
                title="Title\x00\r\nA",
                description="Desc\x00\rB",
                columns=[
                    ReferenceTableColumnInput(
                        name="campaign",
                        data_type=TableDataType.TEXT,
                        nullable=False,
                        description="Col\x00\r\nDesc",
                        semantic_hint="Hint\x00\r\n",
                    )
                ],
            ),
        )
    )

    assert captured["title"] == "Title\nA"
    assert captured["description"] == "Desc\nB"
    columns = captured["columns"]
    assert isinstance(columns, list)
    assert columns[0]["description"] == "Col\nDesc"
    assert columns[0]["semantic_hint"] == "Hint\n"
    assert result.title == "Title\nA"
    assert result.description == "Desc\nB"
    assert result.columns[0].description == "Col\nDesc"
    assert result.columns[0].semantic_hint == "Hint\n"


def test_mutate_rows_sanitizes_source_ref(monkeypatch):
    settings = SimpleNamespace(
        tables_max_cell_length=4_000,
    )
    monkeypatch.setattr(tables_service, "get_settings", lambda: settings)

    table = SimpleNamespace(
        id=uuid4(),
        columns=[
            SimpleNamespace(
                name="campaign",
                data_type=TableDataType.TEXT.value,
                nullable=False,
                description=None,
                semantic_hint=None,
                constraints_json=None,
                default_json=None,
            )
        ],
    )

    async def _get_table(_session, *, table_id, with_columns=True):
        _ = (table_id, with_columns)
        return table

    captured: dict[str, object] = {}

    async def _batch_mutate_rows(_session, *, table, payload, import_job_id=None):
        _ = (table, import_job_id)
        captured["payload"] = payload
        return (1, 0, 0)

    monkeypatch.setattr(tables_service.repo, "get_table", _get_table)
    monkeypatch.setattr(tables_service.repo, "batch_mutate_rows", _batch_mutate_rows)

    result = asyncio.run(
        tables_service.mutate_rows(
            _DummySession(),
            table_id=str(uuid4()),
            payload=RowsBatchInput(
                upserts=[
                    RowUpsert(
                        values_json={"campaign": "Spring"},
                        source_actor=SourceActor.USER,
                        source_ref="src\x00\r\nref",
                    )
                ],
                delete_row_ids=[],
            ),
        )
    )

    assert result.inserted == 1
    payload = captured["payload"]
    assert payload.upserts[0].source_ref == "src\nref"


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
        filename="campaign\x00-report\ud800.csv\r\n",
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

    captured_import_job: dict[str, object] = {}

    async def _create_import_job(_session, **kwargs):
        captured_import_job.update(kwargs)
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
            created_by="import\x00-user\ud800\r\n",
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
    assert captured_import_job["source_filename"] == "campaign-report\ufffd.csv\n"
    assert captured_import_job["created_by"] == "import-user\ufffd\n"


def test_infer_columns_from_file_returns_typed_suggestions(monkeypatch):
    settings = SimpleNamespace(
        tables_max_columns=150,
        tables_max_file_size_bytes=10_000_000,
        tables_max_cell_length=4_000,
    )
    monkeypatch.setattr(tables_service, "get_settings", lambda: settings)

    parsed = ParsedImportData(
        source_format=ImportFormat.CSV,
        rows=[{"campaign": "Spring", "impressions": "1,200"}],
        dataset_name_suggestion="campaigns",
        source_columns={"campaign": "Campaign", "impressions": "Impressions"},
    )
    monkeypatch.setattr(tables_service.importers, "parse_payload", lambda **_: parsed)
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

    response = tables_service.infer_columns_from_file(
        filename="campaigns.csv",
        content=b"campaign,impressions\nSpring,1200\n",
        source_format=ImportFormat.CSV,
        has_header=True,
        delimiter=",",
    )

    assert response.source_format == ImportFormat.CSV
    assert response.dataset_name_suggestion == "campaigns"
    assert response.row_count == 1
    assert response.columns[0].name == "campaign"
    assert response.columns[0].data_type == TableDataType.TEXT
    assert response.columns[1].name == "impressions"
    assert response.columns[1].data_type == TableDataType.INTEGER
