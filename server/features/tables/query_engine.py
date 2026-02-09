from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, and_, asc, cast, desc, func
from sqlalchemy.sql.elements import ClauseElement, ColumnElement

from server.db.models import ReferenceTableColumn, ReferenceTableRow

from .errors import QueryValidationError
from .schema import coerce_cell_value
from .types import AggregateFunction, FilterOperator, RowsQueryInput, TableDataType


@dataclass
class CompiledAggregate:
    alias: str
    expression: ColumnElement[Any]


@dataclass
class CompiledGroupBy:
    field: str
    expression: ColumnElement[Any]


@dataclass
class CompiledQuery:
    where_clauses: list[ClauseElement]
    order_by_clauses: list[ColumnElement[Any]]
    group_by_columns: list[CompiledGroupBy]
    aggregate_columns: list[CompiledAggregate]
    provenance: dict[str, Any]


_SQL_TYPE_MAP: dict[TableDataType, Any] = {
    TableDataType.TEXT: String,
    TableDataType.INTEGER: Integer,
    TableDataType.FLOAT: Float,
    TableDataType.BOOLEAN: Boolean,
    TableDataType.DATE: Date,
    TableDataType.TIMESTAMP: DateTime(timezone=True),
}


def _json_text_expr(column_name: str) -> ColumnElement[Any]:
    raw_expr = ReferenceTableRow.values_json[column_name]
    astext = getattr(raw_expr, "astext", None)
    if astext is not None:
        return astext
    return cast(raw_expr, String)


def _typed_column_expr(column: ReferenceTableColumn) -> ColumnElement[Any]:
    data_type = TableDataType(column.data_type)
    if data_type == TableDataType.JSON:
        return ReferenceTableRow.values_json[column.name]
    text_expr = _json_text_expr(column.name)
    sql_type = _SQL_TYPE_MAP[data_type]
    return cast(text_expr, sql_type)


def _coerce_filter_value(column: ReferenceTableColumn, value: Any, *, max_cell_length: int) -> Any:
    data_type = TableDataType(column.data_type)
    return coerce_cell_value(value, data_type=data_type, max_cell_length=max_cell_length)


def _compile_filter(
    *,
    column: ReferenceTableColumn,
    operator: FilterOperator,
    value: Any,
    max_cell_length: int,
) -> ClauseElement:
    expr = _typed_column_expr(column)
    raw_expr = ReferenceTableRow.values_json[column.name]
    data_type = TableDataType(column.data_type)

    if operator == FilterOperator.IS_NULL:
        return raw_expr.is_(None)
    if operator == FilterOperator.NOT_NULL:
        return raw_expr.is_not(None)

    if operator == FilterOperator.IN:
        if not isinstance(value, list):
            raise QueryValidationError(f"Operator '{operator}' expects an array value.")
        coerced_values = [
            _coerce_filter_value(column, item, max_cell_length=max_cell_length) for item in value
        ]
        return expr.in_(coerced_values)

    if operator == FilterOperator.CONTAINS:
        if data_type == TableDataType.JSON:
            return expr.contains(value)
        text_expr = _json_text_expr(column.name)
        return text_expr.ilike(f"%{str(value)}%")

    if operator == FilterOperator.STARTS_WITH:
        text_expr = _json_text_expr(column.name)
        return text_expr.ilike(f"{str(value)}%")

    if operator == FilterOperator.ENDS_WITH:
        text_expr = _json_text_expr(column.name)
        return text_expr.ilike(f"%{str(value)}")

    coerced = _coerce_filter_value(column, value, max_cell_length=max_cell_length)

    if operator == FilterOperator.EQ:
        return expr == coerced
    if operator == FilterOperator.NEQ:
        return expr != coerced
    if operator == FilterOperator.GT:
        return expr > coerced
    if operator == FilterOperator.GTE:
        return expr >= coerced
    if operator == FilterOperator.LT:
        return expr < coerced
    if operator == FilterOperator.LTE:
        return expr <= coerced

    raise QueryValidationError(f"Unsupported filter operator '{operator}'.")


def compile_query(
    *,
    query: RowsQueryInput,
    columns: list[ReferenceTableColumn],
    max_filters: int,
    max_aggregates: int,
    max_cell_length: int,
) -> CompiledQuery:
    columns_by_name = {column.name: column for column in columns}

    if len(query.filters) > max_filters:
        raise QueryValidationError(f"Too many filters. Maximum is {max_filters}.")
    if len(query.aggregates) > max_aggregates:
        raise QueryValidationError(f"Too many aggregates. Maximum is {max_aggregates}.")

    where_clauses: list[ClauseElement] = []
    for item in query.filters:
        column = columns_by_name.get(item.field)
        if column is None:
            raise QueryValidationError(f"Unknown filter field '{item.field}'.")
        where_clauses.append(
            _compile_filter(
                column=column,
                operator=item.op,
                value=item.value,
                max_cell_length=max_cell_length,
            )
        )

    order_by_clauses: list[ColumnElement[Any]] = []
    for sort in query.sorts:
        column = columns_by_name.get(sort.field)
        if column is None:
            raise QueryValidationError(f"Unknown sort field '{sort.field}'.")
        sort_expr = _typed_column_expr(column)
        order_by_clauses.append(asc(sort_expr) if sort.direction == "asc" else desc(sort_expr))

    group_by_columns: list[CompiledGroupBy] = []
    for field in query.group_by:
        column = columns_by_name.get(field)
        if column is None:
            raise QueryValidationError(f"Unknown group_by field '{field}'.")
        group_by_columns.append(CompiledGroupBy(field=field, expression=_typed_column_expr(column)))

    aggregate_columns: list[CompiledAggregate] = []
    used_aliases: set[str] = set()
    for aggregate in query.aggregates:
        if aggregate.function == AggregateFunction.COUNT:
            if aggregate.field:
                column = columns_by_name.get(aggregate.field)
                if column is None:
                    raise QueryValidationError(f"Unknown aggregate field '{aggregate.field}'.")
                expr = func.count(_typed_column_expr(column))
            else:
                expr = func.count(ReferenceTableRow.id)
            alias = aggregate.alias or "count"
        else:
            field = aggregate.field
            if field is None:
                raise QueryValidationError("Aggregate field is required for non-count functions.")
            column = columns_by_name.get(field)
            if column is None:
                raise QueryValidationError(f"Unknown aggregate field '{field}'.")
            data_type = TableDataType(column.data_type)
            if aggregate.function in {AggregateFunction.SUM, AggregateFunction.AVG} and data_type not in {
                TableDataType.INTEGER,
                TableDataType.FLOAT,
            }:
                raise QueryValidationError(
                    f"Aggregate '{aggregate.function}' requires numeric column '{field}'."
                )
            if aggregate.function in {AggregateFunction.MIN, AggregateFunction.MAX} and data_type == TableDataType.JSON:
                raise QueryValidationError(
                    f"Aggregate '{aggregate.function}' does not support json column '{field}'."
                )

            value_expr = _typed_column_expr(column)
            if aggregate.function == AggregateFunction.SUM:
                expr = func.sum(value_expr)
            elif aggregate.function == AggregateFunction.AVG:
                expr = func.avg(value_expr)
            elif aggregate.function == AggregateFunction.MIN:
                expr = func.min(value_expr)
            elif aggregate.function == AggregateFunction.MAX:
                expr = func.max(value_expr)
            else:  # pragma: no cover - guarded above
                raise QueryValidationError(f"Unsupported aggregate '{aggregate.function}'.")
            alias = aggregate.alias or f"{aggregate.function}_{field}"

        if alias in used_aliases:
            raise QueryValidationError(f"Duplicate aggregate alias '{alias}'.")
        used_aliases.add(alias)
        aggregate_columns.append(CompiledAggregate(alias=alias, expression=expr.label(alias)))

    provenance = {
        "filters": [item.model_dump(mode="json") for item in query.filters],
        "sorts": [item.model_dump(mode="json") for item in query.sorts],
        "group_by": list(query.group_by),
        "aggregates": [item.model_dump(mode="json") for item in query.aggregates],
        "compiled_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z",
    }

    return CompiledQuery(
        where_clauses=where_clauses,
        order_by_clauses=order_by_clauses,
        group_by_columns=group_by_columns,
        aggregate_columns=aggregate_columns,
        provenance=provenance,
    )


def merge_where_clauses(clauses: list[ClauseElement]) -> ClauseElement | None:
    if not clauses:
        return None
    return and_(*clauses)
