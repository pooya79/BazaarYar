from __future__ import annotations

import json
from typing import Any

from langchain.tools import tool

from server.core.config import get_settings
from server.db.session import AsyncSessionLocal
from server.domain.tables import (
    RowsBatchInput,
    RowsQueryInput,
    get_table,
    list_tables,
    mutate_rows,
    query_rows,
)


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True)


@tool(description="List available reference tables and core metadata.")
async def list_tables_tool(limit: int = 20) -> str:
    safe_limit = max(1, min(limit, 100))
    try:
        async with AsyncSessionLocal() as session:
            rows = await list_tables(session, limit=safe_limit, offset=0)

        payload = {
            "tables": [item.model_dump(mode="json") for item in rows],
            "provenance": {"tool": "list_tables", "limit": safe_limit},
        }
        return _dump(payload)
    except Exception as exc:
        return _dump({"error": str(exc), "provenance": {"tool": "list_tables"}})


@tool(description="Describe a reference table including schema and metadata.")
async def describe_table(table_id: str) -> str:
    try:
        async with AsyncSessionLocal() as session:
            table = await get_table(session, table_id=table_id)

        payload = {
            "table": table.model_dump(mode="json"),
            "provenance": {"tool": "describe_table", "table_id": table_id},
        }
        return _dump(payload)
    except Exception as exc:
        return _dump(
            {"error": str(exc), "provenance": {"tool": "describe_table", "table_id": table_id}}
        )


@tool(
    description=(
        "Run a safe query against a reference table. Provide query_json with keys: "
        "filters, sorts, page, page_size, group_by, aggregates."
    )
)
async def query_table(table_id: str, query_json: str = "{}") -> str:
    try:
        query_payload = RowsQueryInput.model_validate(json.loads(query_json))
        async with AsyncSessionLocal() as session:
            table = await get_table(session, table_id=table_id)
            result = await query_rows(session, table_id=table_id, payload=query_payload)

        payload = {
            "table": {
                "id": table.id,
                "name": table.name,
                "columns": [column.model_dump(mode="json") for column in table.columns],
            },
            "result": result.model_dump(mode="json"),
            "provenance": {
                "tool": "query_table",
                "table_id": table_id,
                "limits": {"max_rows": get_settings().tables_max_query_rows},
            },
        }
        return _dump(payload)
    except Exception as exc:
        return _dump({"error": str(exc), "provenance": {"tool": "query_table", "table_id": table_id}})


@tool(
    description=(
        "Mutate table rows with upserts/deletes. Provide batch_json with keys upserts/delete_row_ids. "
        "Writes are allowed only when TABLES_AGENT_WRITE_ENABLED is true."
    )
)
async def mutate_table(table_id: str, batch_json: str) -> str:
    try:
        settings = get_settings()
        if not settings.tables_agent_write_enabled:
            return _dump(
                {
                    "error": "Table write tools are disabled.",
                    "provenance": {
                        "tool": "mutate_table",
                        "table_id": table_id,
                        "write_enabled": False,
                    },
                }
            )

        payload = RowsBatchInput.model_validate(json.loads(batch_json))
        async with AsyncSessionLocal() as session:
            result = await mutate_rows(session, table_id=table_id, payload=payload)

        return _dump(
            {
                "result": result.model_dump(mode="json"),
                "provenance": {
                    "tool": "mutate_table",
                    "table_id": table_id,
                    "write_enabled": True,
                },
            }
        )
    except Exception as exc:
        return _dump({"error": str(exc), "provenance": {"tool": "mutate_table", "table_id": table_id}})


TABLE_TOOLS = [list_tables_tool, describe_table, query_table, mutate_table]
