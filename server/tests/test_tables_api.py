from __future__ import annotations

import importlib
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

tables_api = importlib.import_module("server.api.tables.router")
from server.domain.tables import ExportedPayload
from server.domain.tables.types import (
    QueriedRow,
    ReferenceTableColumn,
    ReferenceTableCreateInput,
    ReferenceTableDetail,
    ReferenceTableSummary,
    ReferenceTableUpdateInput,
    RowsBatchInput,
    RowsBatchResult,
    RowsQueryInput,
    RowsQueryResponse,
    TableDataType,
)
from server.main import app


class _TablesStore:
    def __init__(self):
        self.tables: dict[str, ReferenceTableDetail] = {}
        self.rows: dict[str, list[QueriedRow]] = {}

    async def create_table(self, _session, *, payload: ReferenceTableCreateInput):
        now = datetime.now(timezone.utc)
        table_id = str(uuid4())
        detail = ReferenceTableDetail(
            id=table_id,
            name=payload.name,
            title=payload.title,
            description=payload.description,
            row_count=0,
            created_at=now,
            updated_at=now,
            columns=[
                ReferenceTableColumn(
                    id=str(uuid4()),
                    name=column.name,
                    position=index,
                    data_type=column.data_type,
                    nullable=column.nullable,
                    description=column.description,
                    semantic_hint=column.semantic_hint,
                    constraints_json=column.constraints_json,
                    default_value=column.default_value,
                )
                for index, column in enumerate(payload.columns)
            ],
        )
        self.tables[table_id] = detail
        self.rows[table_id] = []
        return detail

    async def list_tables(self, _session, *, limit=100, offset=0):
        _ = (limit, offset)
        return [
            ReferenceTableSummary(
                id=table.id,
                name=table.name,
                title=table.title,
                description=table.description,
                row_count=table.row_count,
                created_at=table.created_at,
                updated_at=table.updated_at,
            )
            for table in self.tables.values()
        ]

    async def get_table(self, _session, *, table_id):
        return self.tables[str(table_id)]

    async def update_table(self, _session, *, table_id, payload: ReferenceTableUpdateInput):
        existing = self.tables[str(table_id)]
        updated = existing.model_copy(deep=True)
        if payload.title is not None:
            updated.title = payload.title
        if payload.description is not None:
            updated.description = payload.description
        self.tables[str(table_id)] = updated
        return updated

    async def delete_table(self, _session, *, table_id):
        self.tables.pop(str(table_id), None)
        self.rows.pop(str(table_id), None)

    async def query_rows(self, _session, *, table_id, payload: RowsQueryInput):
        table_rows = self.rows.get(str(table_id), [])
        page = payload.page
        page_size = payload.page_size
        start = (page - 1) * page_size
        end = start + page_size
        return RowsQueryResponse(
            total_rows=len(table_rows),
            page=page,
            page_size=page_size,
            rows=table_rows[start:end],
            aggregate_row={"count": len(table_rows)} if payload.aggregates else None,
            grouped_rows=[],
            provenance={"tool": "test"},
        )

    async def mutate_rows(self, _session, *, table_id, payload: RowsBatchInput):
        table_key = str(table_id)
        rows = self.rows.setdefault(table_key, [])
        now = datetime.now(timezone.utc)
        for item in payload.upserts:
            rows.append(
                QueriedRow(
                    id=str(uuid4()),
                    version=1,
                    values_json=item.values_json,
                    created_at=now,
                    updated_at=now,
                )
            )
        deleted = min(len(rows), len(payload.delete_row_ids))
        if deleted:
            del rows[:deleted]
        table = self.tables.get(table_key)
        if table is not None:
            table.row_count = len(rows)
        return RowsBatchResult(inserted=len(payload.upserts), updated=0, deleted=deleted)

    async def start_import(self, _session, *, table_id, payload):
        _ = payload
        return {
            "id": str(uuid4()),
            "table_id": str(table_id),
            "status": "completed",
            "source_filename": "seed.csv",
            "source_format": "csv",
            "total_rows": 2,
            "inserted_rows": 2,
            "updated_rows": 0,
            "deleted_rows": 0,
            "error_count": 0,
            "errors_json": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "inferred_columns": [
                {
                    "name": "campaign",
                    "source_name": "Campaign",
                    "data_type": "text",
                    "confidence": 1.0,
                    "nullable": False,
                    "sample_values": ["Spring"],
                }
            ],
            "provenance": {
                "attachment_id": str(uuid4()),
                "source_format": "csv",
                "dataset_name_suggestion": "seed",
                "source_columns": {"campaign": "Campaign"},
            },
        }

    def infer_columns_from_file(
        self,
        *,
        filename,
        content,
        source_format,
        has_header,
        delimiter,
    ):
        _ = (filename, content, source_format, has_header, delimiter)
        return {
            "source_format": "csv",
            "dataset_name_suggestion": "seed",
            "source_columns": {"campaign": "Campaign", "impressions": "Impressions"},
            "row_count": 2,
            "inferred_columns": [
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
                    "sample_values": [42],
                },
            ],
            "columns": [
                {"name": "campaign", "data_type": "text", "nullable": False},
                {"name": "impressions", "data_type": "integer", "nullable": False},
            ],
        }

    async def get_import_job(self, _session, *, table_id, job_id):
        _ = (table_id, job_id)
        return {
            "id": str(uuid4()),
            "table_id": str(table_id),
            "status": "completed",
            "source_filename": "seed.csv",
            "source_format": "csv",
            "total_rows": 2,
            "inserted_rows": 2,
            "updated_rows": 0,
            "deleted_rows": 0,
            "error_count": 0,
            "errors_json": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }

    async def export_rows(self, _session, *, table_id, payload):
        _ = payload
        table = self.tables[str(table_id)]
        data = b"campaign,impressions\nSpring,42\n"
        return ExportedPayload(
            filename=f"{table.name}.csv",
            media_type="text/csv",
            content=data,
        )


class _DummySession:
    pass


def _patch_store(monkeypatch):
    store = _TablesStore()
    monkeypatch.setattr(tables_api, "create_table", store.create_table)
    monkeypatch.setattr(tables_api, "list_tables", store.list_tables)
    monkeypatch.setattr(tables_api, "get_table", store.get_table)
    monkeypatch.setattr(tables_api, "update_table", store.update_table)
    monkeypatch.setattr(tables_api, "delete_table", store.delete_table)
    monkeypatch.setattr(tables_api, "query_rows", store.query_rows)
    monkeypatch.setattr(tables_api, "mutate_rows", store.mutate_rows)
    monkeypatch.setattr(tables_api, "start_import", store.start_import)
    monkeypatch.setattr(tables_api, "infer_columns_from_file", store.infer_columns_from_file)
    monkeypatch.setattr(tables_api, "get_import_job", store.get_import_job)
    monkeypatch.setattr(tables_api, "export_rows", store.export_rows)

    async def _override_db():
        yield _DummySession()

    app.dependency_overrides[tables_api.get_db_session] = _override_db
    return store


def test_tables_crud_endpoints(monkeypatch):
    _patch_store(monkeypatch)
    client = TestClient(app)

    create_response = client.post(
        "/api/tables",
        json={
            "name": "campaign_metrics",
            "title": "Campaign Metrics",
            "columns": [
                {"name": "campaign", "data_type": TableDataType.TEXT.value, "nullable": False},
                {
                    "name": "impressions",
                    "data_type": TableDataType.INTEGER.value,
                    "nullable": False,
                },
            ],
        },
    )
    assert create_response.status_code == 201
    table_id = create_response.json()["id"]

    list_response = client.get("/api/tables")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == table_id

    detail_response = client.get(f"/api/tables/{table_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "campaign_metrics"

    patch_response = client.patch(
        f"/api/tables/{table_id}",
        json={"title": "Renamed"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Renamed"

    delete_response = client.delete(f"/api/tables/{table_id}")
    assert delete_response.status_code == 204


def test_tables_query_batch_import_export_endpoints(monkeypatch):
    store = _patch_store(monkeypatch)
    client = TestClient(app)

    create_response = client.post(
        "/api/tables",
        json={
            "name": "campaign_metrics",
            "columns": [
                {"name": "campaign", "data_type": "text", "nullable": False},
                {"name": "impressions", "data_type": "integer", "nullable": False},
            ],
        },
    )
    table_id = create_response.json()["id"]

    batch_response = client.post(
        f"/api/tables/{table_id}/rows/batch",
        json={
            "upserts": [
                {
                    "values_json": {"campaign": "Spring", "impressions": 42},
                    "source_actor": "user",
                }
            ],
            "delete_row_ids": [],
        },
    )
    assert batch_response.status_code == 200
    assert batch_response.json()["inserted"] == 1

    query_response = client.post(
        f"/api/tables/{table_id}/rows/query",
        json={"page": 1, "page_size": 50, "filters": [], "sorts": [], "aggregates": []},
    )
    assert query_response.status_code == 200
    assert query_response.json()["total_rows"] == 1

    import_response = client.post(
        f"/api/tables/{table_id}/imports",
        json={"attachment_id": str(uuid4()), "source_format": "csv", "has_header": True},
    )
    assert import_response.status_code == 200
    assert import_response.json()["status"] == "completed"
    assert import_response.json()["provenance"]["dataset_name_suggestion"] == "seed"
    assert import_response.json()["inferred_columns"][0]["source_name"] == "Campaign"

    infer_response = client.post(
        "/api/tables/infer-columns",
        files={"file": ("seed.csv", b"campaign,impressions\nSpring,42\n", "text/csv")},
        data={"source_format": "csv", "has_header": "true"},
    )
    assert infer_response.status_code == 200
    assert infer_response.json()["dataset_name_suggestion"] == "seed"
    assert infer_response.json()["columns"][0]["name"] == "campaign"

    status_response = client.get(f"/api/tables/{table_id}/imports/{uuid4()}")
    assert status_response.status_code == 200

    export_response = client.post(
        f"/api/tables/{table_id}/export",
        json={"format": "csv", "include_header": True},
    )
    assert export_response.status_code == 200
    assert export_response.headers["content-disposition"].endswith('campaign_metrics.csv"')
    assert b"campaign,impressions" in export_response.content
    assert str(table_id) in store.tables


def teardown_function():
    app.dependency_overrides.clear()
