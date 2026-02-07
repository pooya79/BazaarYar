from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from .errors import ColumnValidationError, RowValidationError, SchemaConflictError
from .types import ReferenceTableColumnInput, TableDataType

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


def validate_identifier(value: str, *, field_name: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ColumnValidationError(f"{field_name} cannot be empty.")
    if not _IDENTIFIER_RE.fullmatch(candidate):
        raise ColumnValidationError(
            f"{field_name} must match ^[a-zA-Z_][a-zA-Z0-9_]{{0,62}}$."
        )
    return candidate


def normalize_columns(
    columns: Iterable[ReferenceTableColumnInput],
    *,
    max_columns: int,
    max_cell_length: int,
) -> list[ReferenceTableColumnInput]:
    normalized = [
        ReferenceTableColumnInput(
            name=validate_identifier(column.name, field_name="column name"),
            data_type=column.data_type,
            nullable=column.nullable,
            description=column.description,
            semantic_hint=column.semantic_hint,
            constraints_json=column.constraints_json,
            default_value=column.default_value,
        )
        for column in columns
    ]

    if not normalized:
        raise ColumnValidationError("At least one column is required.")
    if len(normalized) > max_columns:
        raise ColumnValidationError(f"Too many columns. Maximum is {max_columns}.")

    names = [column.name for column in normalized]
    if len(names) != len(set(names)):
        raise ColumnValidationError("Column names must be unique.")

    for column in normalized:
        if column.default_value is not None:
            _ = coerce_cell_value(
                column.default_value,
                data_type=column.data_type,
                max_cell_length=max_cell_length,
            )

    return normalized


def validate_schema_update(
    *,
    existing_columns: Iterable[ReferenceTableColumnInput],
    proposed_columns: Iterable[ReferenceTableColumnInput],
    existing_row_count: int,
    max_columns: int,
    max_cell_length: int,
) -> list[ReferenceTableColumnInput]:
    existing_list = list(existing_columns)
    proposed_list = normalize_columns(
        proposed_columns,
        max_columns=max_columns,
        max_cell_length=max_cell_length,
    )

    if existing_row_count <= 0:
        return proposed_list

    existing_by_name = {column.name: column for column in existing_list}
    proposed_by_name = {column.name: column for column in proposed_list}

    missing = [name for name in existing_by_name if name not in proposed_by_name]
    if missing:
        raise SchemaConflictError(
            "Cannot remove existing columns from a table that already has rows: "
            + ", ".join(sorted(missing))
        )

    for index, existing in enumerate(existing_list):
        proposed = proposed_by_name[existing.name]
        if proposed.data_type != existing.data_type:
            raise SchemaConflictError(
                f"Cannot change data type for column '{existing.name}' when rows already exist."
            )
        if existing.nullable and not proposed.nullable:
            raise SchemaConflictError(
                f"Cannot make nullable column '{existing.name}' non-nullable when rows already exist."
            )
        if proposed_list[index].name != existing.name:
            raise SchemaConflictError(
                "Cannot reorder existing columns when rows already exist."
            )

    for proposed in proposed_list[len(existing_list) :]:
        if not proposed.nullable and proposed.default_value is None:
            raise SchemaConflictError(
                f"New column '{proposed.name}' must be nullable or have a default value."
            )

    return proposed_list


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("Expected datetime string")
    normalized = value.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        raise ValueError("Expected date string")
    return date.fromisoformat(value.strip())


def coerce_cell_value(value: Any, *, data_type: TableDataType, max_cell_length: int) -> Any:
    if value is None:
        return None

    if data_type == TableDataType.TEXT:
        text_value = value if isinstance(value, str) else str(value)
        if len(text_value) > max_cell_length:
            raise ValueError(f"Text value exceeds max length of {max_cell_length}.")
        return text_value

    if data_type == TableDataType.INTEGER:
        if isinstance(value, bool):
            raise ValueError("Boolean is not a valid integer.")
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, Decimal) and value == int(value):
            return int(value)
        if isinstance(value, str):
            return int(value.strip())
        raise ValueError("Invalid integer value.")

    if data_type == TableDataType.FLOAT:
        if isinstance(value, bool):
            raise ValueError("Boolean is not a valid float.")
        if isinstance(value, (int, float, Decimal)):
            return float(value)
        if isinstance(value, str):
            return float(value.strip())
        raise ValueError("Invalid float value.")

    if data_type == TableDataType.BOOLEAN:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y", "on"}:
                return True
            if lowered in {"false", "0", "no", "n", "off"}:
                return False
        if isinstance(value, (int, float)):
            if value == 1:
                return True
            if value == 0:
                return False
        raise ValueError("Invalid boolean value.")

    if data_type == TableDataType.DATE:
        return _parse_date(value).isoformat()

    if data_type == TableDataType.TIMESTAMP:
        return _parse_datetime(value).isoformat()

    if data_type == TableDataType.JSON:
        json.dumps(value)
        return value

    raise ValueError(f"Unsupported data type '{data_type}'.")


def validate_row_values(
    values_json: dict[str, Any],
    *,
    columns: Iterable[ReferenceTableColumnInput],
    max_cell_length: int,
) -> dict[str, Any]:
    if not isinstance(values_json, dict):
        raise RowValidationError("Row values_json must be an object.")

    column_list = list(columns)
    column_map = {column.name: column for column in column_list}
    errors: list[dict[str, Any]] = []

    normalized: dict[str, Any] = {}
    for key in values_json:
        if key not in column_map:
            errors.append({"field": key, "error": "Unknown column."})

    for column in column_list:
        incoming = values_json.get(column.name)
        if incoming is None:
            if column.default_value is not None:
                normalized[column.name] = coerce_cell_value(
                    column.default_value,
                    data_type=column.data_type,
                    max_cell_length=max_cell_length,
                )
                continue
            if not column.nullable:
                errors.append({"field": column.name, "error": "Column is required."})
            normalized[column.name] = None
            continue

        try:
            normalized[column.name] = coerce_cell_value(
                incoming,
                data_type=column.data_type,
                max_cell_length=max_cell_length,
            )
        except Exception as exc:
            errors.append({"field": column.name, "error": str(exc)})

    if errors:
        raise RowValidationError("Row validation failed.", errors=errors)

    return normalized
