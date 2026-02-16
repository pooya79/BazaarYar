from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.db.models import (
    Attachment,
    ReferenceTable,
    ReferenceTableColumn,
    ReferenceTableImportJob,
    ReferenceTableRow,
)
from server.features.shared.text_sanitize import log_sanitization_stats, sanitize_optional_text

from .errors import ImportJobNotFoundError, QueryValidationError, RowValidationError, TableNotFoundError
from .query_engine import compile_query, merge_where_clauses
from .types import ImportFormat, ImportStatus, RowsBatchInput, RowsQueryInput

logger = logging.getLogger(__name__)


def _to_uuid(value: UUID | str, *, field_name: str) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(value)
    except ValueError as exc:
        raise RowValidationError(f"Invalid {field_name}.") from exc


async def get_table(
    session: AsyncSession,
    *,
    table_id: UUID | str,
    with_columns: bool = True,
) -> ReferenceTable:
    table_uuid = _to_uuid(table_id, field_name="table_id")
    stmt = select(ReferenceTable).where(ReferenceTable.id == table_uuid)
    if with_columns:
        stmt = stmt.options(selectinload(ReferenceTable.columns))
    table = (await session.execute(stmt)).scalar_one_or_none()
    if table is None:
        raise TableNotFoundError(f"Table '{table_id}' was not found.")
    return table


async def get_table_by_name(
    session: AsyncSession,
    *,
    name: str,
    with_columns: bool = False,
) -> ReferenceTable | None:
    stmt = select(ReferenceTable).where(ReferenceTable.name == name)
    if with_columns:
        stmt = stmt.options(selectinload(ReferenceTable.columns))
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_tables(
    session: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[ReferenceTable]:
    stmt = (
        select(ReferenceTable)
        .order_by(ReferenceTable.updated_at.desc(), ReferenceTable.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list((await session.execute(stmt)).scalars().all())


async def create_table_with_columns(
    session: AsyncSession,
    *,
    name: str,
    title: str | None,
    description: str | None,
    columns: list[dict[str, Any]],
) -> ReferenceTable:
    clean_title, title_stats = sanitize_optional_text(title, strip=False)
    clean_description, description_stats = sanitize_optional_text(description, strip=False)
    log_sanitization_stats(logger, location="tables.repo.create_table.title", stats=title_stats)
    log_sanitization_stats(
        logger,
        location="tables.repo.create_table.description",
        stats=description_stats,
    )
    table = ReferenceTable(
        name=name,
        title=clean_title,
        description=clean_description,
    )
    session.add(table)
    await session.flush()

    for position, column in enumerate(columns):
        clean_column_description, column_description_stats = sanitize_optional_text(
            column.get("description"),
            strip=False,
        )
        clean_column_semantic_hint, semantic_hint_stats = sanitize_optional_text(
            column.get("semantic_hint"),
            strip=False,
        )
        log_sanitization_stats(
            logger,
            location=f"tables.repo.create_table.columns.description.{column['name']}",
            stats=column_description_stats,
        )
        log_sanitization_stats(
            logger,
            location=f"tables.repo.create_table.columns.semantic_hint.{column['name']}",
            stats=semantic_hint_stats,
        )
        session.add(
            ReferenceTableColumn(
                table_id=table.id,
                name=column["name"],
                position=position,
                data_type=column["data_type"],
                nullable=column["nullable"],
                description=clean_column_description,
                semantic_hint=clean_column_semantic_hint,
                constraints_json=column.get("constraints_json"),
                default_json=column.get("default_value"),
            )
        )

    await session.commit()
    return await get_table(session, table_id=table.id, with_columns=True)


async def replace_columns(
    session: AsyncSession,
    *,
    table: ReferenceTable,
    columns: list[dict[str, Any]],
) -> ReferenceTable:
    await session.execute(
        delete(ReferenceTableColumn).where(ReferenceTableColumn.table_id == table.id)
    )
    await session.flush()

    for position, column in enumerate(columns):
        clean_column_description, column_description_stats = sanitize_optional_text(
            column.get("description"),
            strip=False,
        )
        clean_column_semantic_hint, semantic_hint_stats = sanitize_optional_text(
            column.get("semantic_hint"),
            strip=False,
        )
        log_sanitization_stats(
            logger,
            location=f"tables.repo.replace_columns.description.{column['name']}",
            stats=column_description_stats,
        )
        log_sanitization_stats(
            logger,
            location=f"tables.repo.replace_columns.semantic_hint.{column['name']}",
            stats=semantic_hint_stats,
        )
        session.add(
            ReferenceTableColumn(
                table_id=table.id,
                name=column["name"],
                position=position,
                data_type=column["data_type"],
                nullable=column["nullable"],
                description=clean_column_description,
                semantic_hint=clean_column_semantic_hint,
                constraints_json=column.get("constraints_json"),
                default_json=column.get("default_value"),
            )
        )

    await session.commit()
    return await get_table(session, table_id=table.id, with_columns=True)


async def update_table_metadata(
    session: AsyncSession,
    *,
    table: ReferenceTable,
    title: str | None,
    description: str | None,
) -> ReferenceTable:
    clean_title, title_stats = sanitize_optional_text(title, strip=False)
    clean_description, description_stats = sanitize_optional_text(description, strip=False)
    log_sanitization_stats(
        logger,
        location="tables.repo.update_table_metadata.title",
        stats=title_stats,
    )
    log_sanitization_stats(
        logger,
        location="tables.repo.update_table_metadata.description",
        stats=description_stats,
    )
    table.title = clean_title
    table.description = clean_description
    await session.commit()
    return await get_table(session, table_id=table.id, with_columns=True)


async def delete_table(session: AsyncSession, *, table: ReferenceTable) -> None:
    await session.delete(table)
    await session.commit()


async def query_rows(
    session: AsyncSession,
    *,
    table: ReferenceTable,
    query: RowsQueryInput,
    max_filters: int,
    max_aggregates: int,
    max_page_size: int,
    max_cell_length: int,
    timeout_ms: int,
) -> dict[str, Any]:
    if query.page_size > max_page_size:
        raise QueryValidationError(f"page_size exceeds max limit of {max_page_size}.")

    compiled = compile_query(
        query=query,
        columns=table.columns,
        max_filters=max_filters,
        max_aggregates=max_aggregates,
        max_cell_length=max_cell_length,
    )

    where_clauses = [ReferenceTableRow.table_id == table.id, *compiled.where_clauses]
    merged_where = merge_where_clauses(where_clauses)

    count_stmt = select(func.count(ReferenceTableRow.id))
    if merged_where is not None:
        count_stmt = count_stmt.where(merged_where)

    base_rows_stmt = select(ReferenceTableRow)
    if merged_where is not None:
        base_rows_stmt = base_rows_stmt.where(merged_where)

    if compiled.order_by_clauses:
        base_rows_stmt = base_rows_stmt.order_by(*compiled.order_by_clauses)
    else:
        base_rows_stmt = base_rows_stmt.order_by(ReferenceTableRow.created_at.desc(), ReferenceTableRow.id.desc())

    offset = (query.page - 1) * query.page_size
    rows_stmt = base_rows_stmt.offset(offset).limit(query.page_size)

    async def _execute_payload() -> dict[str, Any]:
        total_rows = int((await session.execute(count_stmt)).scalar_one() or 0)
        rows = list((await session.execute(rows_stmt)).scalars().all())

        aggregate_row: dict[str, Any] | None = None
        grouped_rows: list[dict[str, Any]] = []

        if compiled.aggregate_columns:
            if compiled.group_by_columns:
                group_select = [
                    item.expression.label(item.field) for item in compiled.group_by_columns
                ] + [item.expression for item in compiled.aggregate_columns]
                group_stmt = select(*group_select)
                if merged_where is not None:
                    group_stmt = group_stmt.where(merged_where)
                group_stmt = group_stmt.group_by(
                    *[item.expression for item in compiled.group_by_columns]
                )
                group_stmt = group_stmt.offset(offset).limit(query.page_size)
                group_rows = (await session.execute(group_stmt)).mappings().all()
                grouped_rows = [dict(row) for row in group_rows]
            else:
                aggregate_stmt = select(*[item.expression for item in compiled.aggregate_columns])
                if merged_where is not None:
                    aggregate_stmt = aggregate_stmt.where(merged_where)
                aggregate_mapping = (await session.execute(aggregate_stmt)).mappings().first()
                aggregate_row = dict(aggregate_mapping) if aggregate_mapping is not None else {}

        return {
            "total_rows": total_rows,
            "rows": rows,
            "aggregate_row": aggregate_row,
            "grouped_rows": grouped_rows,
            "provenance": compiled.provenance,
        }

    try:
        return await asyncio.wait_for(_execute_payload(), timeout=timeout_ms / 1000)
    except TimeoutError as exc:
        raise QueryValidationError(
            f"Query exceeded timeout of {timeout_ms}ms. Reduce filters/grouping complexity."
        ) from exc


async def batch_mutate_rows(
    session: AsyncSession,
    *,
    table: ReferenceTable,
    payload: RowsBatchInput,
    import_job_id: UUID | None = None,
) -> tuple[int, int, int]:
    inserted = 0
    updated = 0

    for upsert in payload.upserts:
        row: ReferenceTableRow | None = None
        row_uuid: UUID | None = None
        if upsert.row_id:
            row_uuid = _to_uuid(upsert.row_id, field_name="row_id")
            row = await session.get(ReferenceTableRow, row_uuid)
            if row is not None and row.table_id != table.id:
                raise RowValidationError(
                    f"Row '{upsert.row_id}' does not belong to table '{table.id}'."
                )

        if row is None:
            clean_source_ref, source_ref_stats = sanitize_optional_text(upsert.source_ref, strip=False)
            log_sanitization_stats(
                logger,
                location="tables.repo.batch_mutate_rows.insert.source_ref",
                stats=source_ref_stats,
            )
            session.add(
                ReferenceTableRow(
                    id=row_uuid,
                    table_id=table.id,
                    import_job_id=import_job_id,
                    values_json=upsert.values_json,
                    source_actor=upsert.source_actor.value,
                    source_ref=clean_source_ref,
                    created_by=clean_source_ref,
                    updated_by=clean_source_ref,
                )
            )
            inserted += 1
            continue

        clean_source_ref, source_ref_stats = sanitize_optional_text(upsert.source_ref, strip=False)
        log_sanitization_stats(
            logger,
            location="tables.repo.batch_mutate_rows.update.source_ref",
            stats=source_ref_stats,
        )
        row.values_json = upsert.values_json
        row.version += 1
        row.source_actor = upsert.source_actor.value
        row.source_ref = clean_source_ref
        row.updated_by = clean_source_ref
        if import_job_id is not None:
            row.import_job_id = import_job_id
        updated += 1

    deleted = 0
    if payload.delete_row_ids:
        delete_ids = [_to_uuid(item, field_name="delete_row_id") for item in payload.delete_row_ids]
        delete_stmt = delete(ReferenceTableRow).where(
            and_(
                ReferenceTableRow.table_id == table.id,
                ReferenceTableRow.id.in_(delete_ids),
            )
        )
        result = await session.execute(delete_stmt)
        deleted = int(result.rowcount or 0)

    await session.flush()
    table.row_count = int(
        (
            await session.execute(
                select(func.count(ReferenceTableRow.id)).where(ReferenceTableRow.table_id == table.id)
            )
        ).scalar_one()
        or 0
    )
    await session.commit()

    return inserted, updated, deleted


async def get_attachment_for_import(
    session: AsyncSession,
    *,
    attachment_id: UUID,
) -> Attachment | None:
    return await session.get(Attachment, attachment_id)


async def create_import_job(
    session: AsyncSession,
    *,
    table_id: UUID,
    attachment_id: UUID,
    source_filename: str | None,
    source_format: ImportFormat | None,
    created_by: str | None,
) -> ReferenceTableImportJob:
    clean_source_filename, source_filename_stats = sanitize_optional_text(
        source_filename,
        strip=False,
    )
    clean_created_by, created_by_stats = sanitize_optional_text(created_by, strip=False)
    log_sanitization_stats(
        logger,
        location="tables.repo.create_import_job.source_filename",
        stats=source_filename_stats,
    )
    log_sanitization_stats(
        logger,
        location="tables.repo.create_import_job.created_by",
        stats=created_by_stats,
    )
    job = ReferenceTableImportJob(
        table_id=table_id,
        attachment_id=attachment_id,
        status=ImportStatus.PENDING.value,
        source_filename=clean_source_filename,
        source_format=source_format.value if source_format else None,
        created_by=clean_created_by,
        errors_json=[],
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def get_import_job(
    session: AsyncSession,
    *,
    table_id: UUID | str,
    job_id: UUID | str,
) -> ReferenceTableImportJob:
    table_uuid = _to_uuid(table_id, field_name="table_id")
    job_uuid = _to_uuid(job_id, field_name="job_id")
    stmt = select(ReferenceTableImportJob).where(
        and_(
            ReferenceTableImportJob.id == job_uuid,
            ReferenceTableImportJob.table_id == table_uuid,
        )
    )
    job = (await session.execute(stmt)).scalar_one_or_none()
    if job is None:
        raise ImportJobNotFoundError(f"Import job '{job_id}' was not found.")
    return job


async def mark_import_job_running(
    session: AsyncSession,
    *,
    job: ReferenceTableImportJob,
) -> ReferenceTableImportJob:
    from datetime import datetime, timezone

    job.status = ImportStatus.RUNNING.value
    job.started_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(job)
    return job


async def finish_import_job(
    session: AsyncSession,
    *,
    job: ReferenceTableImportJob,
    status: ImportStatus,
    total_rows: int,
    inserted_rows: int,
    updated_rows: int,
    deleted_rows: int,
    errors_json: list[dict[str, Any]],
) -> ReferenceTableImportJob:
    from datetime import datetime, timezone

    job.status = status.value
    job.total_rows = total_rows
    job.inserted_rows = inserted_rows
    job.updated_rows = updated_rows
    job.deleted_rows = deleted_rows
    job.error_count = len(errors_json)
    job.errors_json = errors_json
    job.finished_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(job)
    return job
