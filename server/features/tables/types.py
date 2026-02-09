from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TableDataType(str, Enum):
    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"
    JSON = "json"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class FilterOperator(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_NULL = "is_null"
    NOT_NULL = "not_null"


class AggregateFunction(str, Enum):
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"


class ImportStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"


class SourceActor(str, Enum):
    USER = "user"
    AGENT = "agent"
    IMPORT = "import"


class ImportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"


class ReferenceTableColumnInput(BaseModel):
    name: str = Field(min_length=1, max_length=63)
    data_type: TableDataType
    nullable: bool = True
    description: str | None = Field(default=None, max_length=1024)
    semantic_hint: str | None = Field(default=None, max_length=128)
    constraints_json: dict[str, Any] | None = None
    default_value: Any | None = None


class ReferenceTableCreateInput(BaseModel):
    name: str = Field(min_length=1, max_length=63)
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2048)
    columns: list[ReferenceTableColumnInput] = Field(min_length=1)


class ReferenceTableUpdateInput(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2048)
    columns: list[ReferenceTableColumnInput] | None = None


class ReferenceTableColumn(BaseModel):
    id: str
    name: str
    position: int
    data_type: TableDataType
    nullable: bool
    description: str | None
    semantic_hint: str | None
    constraints_json: dict[str, Any] | None
    default_value: Any | None


class ReferenceTableSummary(BaseModel):
    id: str
    name: str
    title: str | None
    description: str | None
    row_count: int
    created_at: datetime
    updated_at: datetime


class ReferenceTableDetail(ReferenceTableSummary):
    columns: list[ReferenceTableColumn]


class QueryFilter(BaseModel):
    field: str = Field(min_length=1, max_length=63)
    op: FilterOperator
    value: Any | None = None


class QuerySort(BaseModel):
    field: str = Field(min_length=1, max_length=63)
    direction: SortDirection = SortDirection.ASC


class QueryAggregate(BaseModel):
    function: AggregateFunction
    field: str | None = Field(default=None, max_length=63)
    alias: str | None = Field(default=None, max_length=63)

    @model_validator(mode="after")
    def validate_field_requirement(self) -> QueryAggregate:
        if self.function == AggregateFunction.COUNT:
            return self
        if not self.field:
            raise ValueError("Aggregate field is required for non-count functions.")
        return self


class RowsQueryInput(BaseModel):
    filters: list[QueryFilter] = Field(default_factory=list)
    sorts: list[QuerySort] = Field(default_factory=list)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    group_by: list[str] = Field(default_factory=list)
    aggregates: list[QueryAggregate] = Field(default_factory=list)


class QueriedRow(BaseModel):
    id: str
    version: int
    values_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RowsQueryResponse(BaseModel):
    total_rows: int
    page: int
    page_size: int
    rows: list[QueriedRow]
    aggregate_row: dict[str, Any] | None = None
    grouped_rows: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any]


class RowUpsert(BaseModel):
    row_id: str | None = None
    values_json: dict[str, Any]
    source_actor: SourceActor = SourceActor.USER
    source_ref: str | None = Field(default=None, max_length=255)


class RowsBatchInput(BaseModel):
    upserts: list[RowUpsert] = Field(default_factory=list)
    delete_row_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_has_operation(self) -> RowsBatchInput:
        if not self.upserts and not self.delete_row_ids:
            raise ValueError("Provide at least one upsert or delete operation.")
        return self


class RowsBatchResult(BaseModel):
    inserted: int
    updated: int
    deleted: int


class ImportStartInput(BaseModel):
    attachment_id: str
    source_format: ImportFormat | None = None
    has_header: bool = True
    delimiter: str | None = None
    column_overrides: dict[str, TableDataType] = Field(default_factory=dict)


class InferredColumn(BaseModel):
    name: str
    source_name: str
    data_type: TableDataType
    confidence: float = Field(ge=0, le=1)
    nullable: bool
    sample_values: list[Any] = Field(default_factory=list)


class InferColumnsResponse(BaseModel):
    source_format: ImportFormat
    dataset_name_suggestion: str
    source_columns: dict[str, str]
    row_count: int
    inferred_columns: list[InferredColumn]
    columns: list[ReferenceTableColumnInput]


class ImportJobSummary(BaseModel):
    id: str
    table_id: str
    status: ImportStatus
    source_filename: str | None
    source_format: ImportFormat | None
    total_rows: int
    inserted_rows: int
    updated_rows: int
    deleted_rows: int
    error_count: int
    errors_json: list[dict[str, Any]]
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    inferred_columns: list[dict[str, Any]] | None = None
    provenance: dict[str, Any] | None = None


class ExportInput(BaseModel):
    format: ExportFormat
    query: RowsQueryInput | None = None
    include_header: bool = True
