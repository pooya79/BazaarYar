from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import get_settings
from server.db.models import ReferenceTable, ReferenceTableImportJob

from . import importers, repository, schema
from .errors import ImportFormatError, QueryValidationError, RowValidationError
from .types import (
    ExportFormat,
    ExportInput,
    InferColumnsResponse,
    InferredColumn,
    ImportFormat,
    ImportJobSummary,
    ImportStartInput,
    ImportStatus,
    QueriedRow,
    ReferenceTableColumn,
    ReferenceTableColumnInput,
    ReferenceTableCreateInput,
    ReferenceTableDetail,
    ReferenceTableSummary,
    ReferenceTableUpdateInput,
    RowUpsert,
    RowsBatchInput,
    RowsBatchResult,
    RowsQueryInput,
    RowsQueryResponse,
    SourceActor,
    TableDataType,
)


def _table_column_to_input(column) -> ReferenceTableColumnInput:
    return ReferenceTableColumnInput(
        name=column.name,
        data_type=column.data_type,
        nullable=column.nullable,
        description=column.description,
        semantic_hint=column.semantic_hint,
        constraints_json=column.constraints_json,
        default_value=column.default_json,
    )


def _table_to_summary(table: ReferenceTable) -> ReferenceTableSummary:
    return ReferenceTableSummary(
        id=str(table.id),
        name=table.name,
        title=table.title,
        description=table.description,
        row_count=table.row_count,
        created_at=table.created_at,
        updated_at=table.updated_at,
    )


def _table_to_detail(table: ReferenceTable) -> ReferenceTableDetail:
    return ReferenceTableDetail(
        **_table_to_summary(table).model_dump(),
        columns=[
            ReferenceTableColumn(
                id=str(column.id),
                name=column.name,
                position=column.position,
                data_type=column.data_type,
                nullable=column.nullable,
                description=column.description,
                semantic_hint=column.semantic_hint,
                constraints_json=column.constraints_json,
                default_value=column.default_json,
            )
            for column in sorted(table.columns, key=lambda item: item.position)
        ],
    )


def _import_job_to_summary(job: ReferenceTableImportJob) -> dict[str, Any]:
    source_format = None
    if job.source_format:
        try:
            source_format = ImportFormat(job.source_format)
        except ValueError:
            source_format = None

    return ImportJobSummary(
        id=str(job.id),
        table_id=str(job.table_id),
        status=job.status,
        source_filename=job.source_filename,
        source_format=source_format,
        total_rows=job.total_rows,
        inserted_rows=job.inserted_rows,
        updated_rows=job.updated_rows,
        deleted_rows=job.deleted_rows,
        error_count=job.error_count,
        errors_json=job.errors_json,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    ).model_dump(mode="json")


async def create_table(
    session: AsyncSession,
    *,
    payload: ReferenceTableCreateInput,
) -> ReferenceTableDetail:
    settings = get_settings()
    table_name = schema.validate_identifier(payload.name, field_name="table name")
    if await repository.get_table_by_name(session, name=table_name):
        raise RowValidationError(f"Table '{table_name}' already exists.")

    normalized_columns = schema.normalize_columns(
        payload.columns,
        max_columns=settings.tables_max_columns,
        max_cell_length=settings.tables_max_cell_length,
    )

    table = await repository.create_table_with_columns(
        session,
        name=table_name,
        title=payload.title,
        description=payload.description,
        columns=[column.model_dump(mode="json") for column in normalized_columns],
    )
    return _table_to_detail(table)


async def list_tables(session: AsyncSession, *, limit: int = 100, offset: int = 0) -> list[ReferenceTableSummary]:
    items = await repository.list_tables(session, limit=limit, offset=offset)
    return [_table_to_summary(item) for item in items]


async def get_table(session: AsyncSession, *, table_id: UUID | str) -> ReferenceTableDetail:
    table = await repository.get_table(session, table_id=table_id, with_columns=True)
    return _table_to_detail(table)


async def update_table(
    session: AsyncSession,
    *,
    table_id: UUID | str,
    payload: ReferenceTableUpdateInput,
) -> ReferenceTableDetail:
    settings = get_settings()
    table = await repository.get_table(session, table_id=table_id, with_columns=True)

    if payload.columns is not None:
        existing_columns = [_table_column_to_input(column) for column in table.columns]
        next_columns = schema.validate_schema_update(
            existing_columns=existing_columns,
            proposed_columns=payload.columns,
            existing_row_count=table.row_count,
            max_columns=settings.tables_max_columns,
            max_cell_length=settings.tables_max_cell_length,
        )
        table = await repository.replace_columns(
            session,
            table=table,
            columns=[column.model_dump(mode="json") for column in next_columns],
        )

    title = payload.title if payload.title is not None else table.title
    description = payload.description if payload.description is not None else table.description
    table = await repository.update_table_metadata(
        session,
        table=table,
        title=title,
        description=description,
    )
    return _table_to_detail(table)


async def delete_table(session: AsyncSession, *, table_id: UUID | str) -> None:
    table = await repository.get_table(session, table_id=table_id, with_columns=False)
    await repository.delete_table(session, table=table)


async def query_rows(
    session: AsyncSession,
    *,
    table_id: UUID | str,
    payload: RowsQueryInput,
) -> RowsQueryResponse:
    settings = get_settings()
    table = await repository.get_table(session, table_id=table_id, with_columns=True)
    query_payload = payload.model_copy(deep=True)
    query_payload.page_size = min(query_payload.page_size, settings.tables_max_query_rows)

    result = await repository.query_rows(
        session,
        table=table,
        query=query_payload,
        max_filters=settings.tables_max_filters,
        max_aggregates=settings.tables_max_aggregates,
        max_page_size=settings.tables_max_query_rows,
        max_cell_length=settings.tables_max_cell_length,
        timeout_ms=settings.tables_query_timeout_ms,
    )

    return RowsQueryResponse(
        total_rows=result["total_rows"],
        page=query_payload.page,
        page_size=query_payload.page_size,
        rows=[
            QueriedRow(
                id=str(item.id),
                version=item.version,
                values_json=item.values_json,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in result["rows"]
        ],
        aggregate_row=result["aggregate_row"],
        grouped_rows=result["grouped_rows"],
        provenance=result["provenance"],
    )


async def mutate_rows(
    session: AsyncSession,
    *,
    table_id: UUID | str,
    payload: RowsBatchInput,
    import_job_id: UUID | None = None,
) -> RowsBatchResult:
    settings = get_settings()
    table = await repository.get_table(session, table_id=table_id, with_columns=True)
    schema_columns = [_table_column_to_input(column) for column in table.columns]

    normalized_upserts: list[RowUpsert] = []
    for row in payload.upserts:
        normalized_values = schema.validate_row_values(
            row.values_json,
            columns=schema_columns,
            max_cell_length=settings.tables_max_cell_length,
        )
        normalized_upserts.append(
            RowUpsert(
                row_id=row.row_id,
                values_json=normalized_values,
                source_actor=row.source_actor,
                source_ref=row.source_ref,
            )
        )

    inserted, updated, deleted = await repository.batch_mutate_rows(
        session,
        table=table,
        payload=RowsBatchInput(upserts=normalized_upserts, delete_row_ids=payload.delete_row_ids),
        import_job_id=import_job_id,
    )
    return RowsBatchResult(inserted=inserted, updated=updated, deleted=deleted)


def infer_columns_from_file(
    *,
    filename: str | None,
    content: bytes,
    source_format: ImportFormat | None,
    has_header: bool,
    delimiter: str | None,
) -> InferColumnsResponse:
    settings = get_settings()
    normalized_filename = (filename or "").strip()
    if not normalized_filename:
        raise ImportFormatError("Uploaded file is missing a filename.")
    if not content:
        raise ImportFormatError(f"File '{normalized_filename}' is empty.")
    if len(content) > settings.tables_max_file_size_bytes:
        raise ImportFormatError(
            f"Attachment exceeds max size of {settings.tables_max_file_size_bytes} bytes."
        )

    parsed = importers.parse_payload(
        payload=content,
        filename=normalized_filename,
        source_format=source_format,
        has_header=has_header,
        delimiter=delimiter,
    )
    inferred_columns = importers.infer_columns(
        parsed.rows,
        max_columns=settings.tables_max_columns,
        source_columns=parsed.source_columns,
    )

    suggested_columns = schema.normalize_columns(
        [
            ReferenceTableColumnInput(
                name=item["name"],
                data_type=TableDataType(item["data_type"]),
                nullable=bool(item["nullable"]),
            )
            for item in inferred_columns
        ],
        max_columns=settings.tables_max_columns,
        max_cell_length=settings.tables_max_cell_length,
    )

    return InferColumnsResponse(
        source_format=parsed.source_format,
        dataset_name_suggestion=parsed.dataset_name_suggestion,
        source_columns=parsed.source_columns,
        row_count=len(parsed.rows),
        inferred_columns=[InferredColumn.model_validate(item) for item in inferred_columns],
        columns=suggested_columns,
    )


async def start_import(
    session: AsyncSession,
    *,
    table_id: UUID | str,
    payload: ImportStartInput,
    created_by: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    table = await repository.get_table(session, table_id=table_id, with_columns=True)

    try:
        attachment_id = UUID(payload.attachment_id)
    except ValueError as exc:
        raise RowValidationError("Invalid attachment_id.") from exc

    attachment = await repository.get_attachment_for_import(session, attachment_id=attachment_id)
    if attachment is None:
        raise RowValidationError(f"Attachment '{payload.attachment_id}' was not found.")
    if attachment.size_bytes > settings.tables_max_file_size_bytes:
        raise ImportFormatError(
            f"Attachment exceeds max size of {settings.tables_max_file_size_bytes} bytes."
        )

    job = await repository.create_import_job(
        session,
        table_id=table.id,
        attachment_id=attachment_id,
        source_filename=attachment.filename,
        source_format=payload.source_format,
        created_by=created_by,
    )
    job = await repository.mark_import_job_running(session, job=job)

    try:
        parsed = importers.parse_attachment(
            attachment,
            source_format=payload.source_format,
            has_header=payload.has_header,
            delimiter=payload.delimiter,
        )
        inferred_columns = importers.infer_columns(
            parsed.rows,
            max_columns=settings.tables_max_columns,
            source_columns=parsed.source_columns,
        )

        table_columns = [_table_column_to_input(column) for column in table.columns]
        overrides = payload.column_overrides or {}
        if overrides:
            for column in table_columns:
                if column.name in overrides:
                    column.data_type = overrides[column.name]

        normalized_rows, row_errors = importers.validate_import_rows(
            parsed.rows,
            columns=table_columns,
            max_rows=settings.tables_max_import_rows,
            max_cell_length=settings.tables_max_cell_length,
        )

        inserted = 0
        updated = 0
        deleted = 0
        if normalized_rows:
            mutation_result = await mutate_rows(
                session,
                table_id=table.id,
                payload=RowsBatchInput(
                    upserts=[
                        RowUpsert(
                            values_json=row,
                            source_actor=SourceActor.IMPORT,
                            source_ref=str(job.id),
                        )
                        for row in normalized_rows
                    ],
                    delete_row_ids=[],
                ),
                import_job_id=job.id,
            )
            inserted = mutation_result.inserted
            updated = mutation_result.updated
            deleted = mutation_result.deleted

        status = ImportStatus.COMPLETED if normalized_rows or not row_errors else ImportStatus.FAILED
        job = await repository.finish_import_job(
            session,
            job=job,
            status=status,
            total_rows=len(parsed.rows),
            inserted_rows=inserted,
            updated_rows=updated,
            deleted_rows=deleted,
            errors_json=row_errors,
        )

        response = _import_job_to_summary(job)
        response["inferred_columns"] = inferred_columns
        response["provenance"] = {
            "attachment_id": payload.attachment_id,
            "source_format": parsed.source_format.value,
            "dataset_name_suggestion": parsed.dataset_name_suggestion,
            "source_columns": parsed.source_columns,
        }
        return response
    except Exception as exc:
        await repository.finish_import_job(
            session,
            job=job,
            status=ImportStatus.FAILED,
            total_rows=0,
            inserted_rows=0,
            updated_rows=0,
            deleted_rows=0,
            errors_json=[{"error": str(exc)}],
        )
        raise


async def get_import_job(
    session: AsyncSession,
    *,
    table_id: UUID | str,
    job_id: UUID | str,
) -> dict[str, Any]:
    job = await repository.get_import_job(session, table_id=table_id, job_id=job_id)
    return _import_job_to_summary(job)


@dataclass
class ExportedPayload:
    filename: str
    media_type: str
    content: bytes


async def export_rows(
    session: AsyncSession,
    *,
    table_id: UUID | str,
    payload: ExportInput,
) -> ExportedPayload:
    settings = get_settings()
    table = await repository.get_table(session, table_id=table_id, with_columns=True)
    query_payload = payload.query or RowsQueryInput()
    query_payload = query_payload.model_copy(deep=True)
    query_payload.page = 1
    query_payload.page_size = settings.tables_export_max_rows

    result = await query_rows(session, table_id=table.id, payload=query_payload)

    if result.total_rows > settings.tables_export_max_rows:
        raise QueryValidationError(
            f"Export exceeds max rows limit ({settings.tables_export_max_rows})."
        )

    if result.grouped_rows:
        rows_to_export = result.grouped_rows
        headers = list(result.grouped_rows[0].keys()) if result.grouped_rows else []
    else:
        rows_to_export = [row.values_json for row in result.rows]
        headers = [column.name for column in sorted(table.columns, key=lambda item: item.position)]

    if payload.format == ExportFormat.JSON:
        body = json.dumps(rows_to_export, ensure_ascii=True, indent=2).encode("utf-8")
        return ExportedPayload(
            filename=f"{table.name}.json",
            media_type="application/json",
            content=body,
        )

    if payload.format == ExportFormat.CSV:
        stream = io.StringIO()
        writer = csv.writer(stream)
        if payload.include_header and headers:
            writer.writerow(headers)
        for row in rows_to_export:
            writer.writerow([row.get(header) for header in headers])
        return ExportedPayload(
            filename=f"{table.name}.csv",
            media_type="text/csv",
            content=stream.getvalue().encode("utf-8"),
        )

    if payload.format == ExportFormat.XLSX:
        try:
            from openpyxl import Workbook
        except Exception as exc:
            raise ImportFormatError(
                "XLSX export requires openpyxl. Install it or export as csv/json."
            ) from exc

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "export"
        if payload.include_header and headers:
            sheet.append(headers)
        for row in rows_to_export:
            sheet.append([row.get(header) for header in headers])

        content = io.BytesIO()
        workbook.save(content)
        return ExportedPayload(
            filename=f"{table.name}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.getvalue(),
        )

    raise QueryValidationError(f"Unsupported export format '{payload.format}'.")
