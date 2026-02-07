from __future__ import annotations

from uuid import uuid4

import pytest

from server.db.models import ReferenceTableColumn
from server.domain.tables.errors import QueryValidationError, SchemaConflictError
from server.domain.tables.query_engine import compile_query
from server.domain.tables.schema import validate_row_values, validate_schema_update
from server.domain.tables.types import (
    AggregateFunction,
    QueryAggregate,
    ReferenceTableColumnInput,
    RowsQueryInput,
    TableDataType,
)


def test_validate_row_values_coerces_and_reports_unknown_fields():
    columns = [
        ReferenceTableColumnInput(name="campaign", data_type=TableDataType.TEXT, nullable=False),
        ReferenceTableColumnInput(name="impressions", data_type=TableDataType.INTEGER, nullable=False),
        ReferenceTableColumnInput(name="ctr", data_type=TableDataType.FLOAT, nullable=True),
    ]

    normalized = validate_row_values(
        {"campaign": "Spring", "impressions": "42", "ctr": "0.17"},
        columns=columns,
        max_cell_length=100,
    )

    assert normalized["campaign"] == "Spring"
    assert normalized["impressions"] == 42
    assert normalized["ctr"] == 0.17

    with pytest.raises(Exception):
        validate_row_values(
            {"campaign": "Spring", "impressions": "42", "unknown": "x"},
            columns=columns,
            max_cell_length=100,
        )


def test_validate_schema_update_disallows_type_change_when_rows_exist():
    existing = [
        ReferenceTableColumnInput(name="campaign", data_type=TableDataType.TEXT, nullable=False),
        ReferenceTableColumnInput(name="impressions", data_type=TableDataType.INTEGER, nullable=False),
    ]
    proposed = [
        ReferenceTableColumnInput(name="campaign", data_type=TableDataType.TEXT, nullable=False),
        ReferenceTableColumnInput(name="impressions", data_type=TableDataType.FLOAT, nullable=False),
    ]

    with pytest.raises(SchemaConflictError):
        validate_schema_update(
            existing_columns=existing,
            proposed_columns=proposed,
            existing_row_count=5,
            max_columns=20,
            max_cell_length=100,
        )


def test_compile_query_rejects_sum_over_text_column():
    columns = [
        ReferenceTableColumn(
            id=uuid4(),
            table_id=uuid4(),
            name="campaign",
            position=0,
            data_type="text",
            nullable=False,
        )
    ]

    with pytest.raises(QueryValidationError):
        compile_query(
            query=RowsQueryInput(
                aggregates=[
                    QueryAggregate(
                        function=AggregateFunction.SUM,
                        field="campaign",
                        alias="total",
                    )
                ]
            ),
            columns=columns,
            max_filters=10,
            max_aggregates=10,
            max_cell_length=200,
        )
