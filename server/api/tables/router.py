from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import get_settings
from server.db.session import get_db_session
from server.domain.tables import (
    ColumnValidationError,
    ExportInput,
    InferColumnsResponse,
    ImportFormat,
    ImportFormatError,
    ImportJobNotFoundError,
    ImportStartInput,
    QueryValidationError,
    ReferenceTableCreateInput,
    ReferenceTableDetail,
    ReferenceTableSummary,
    ReferenceTableUpdateInput,
    RowValidationError,
    RowsBatchInput,
    RowsBatchResult,
    RowsQueryInput,
    RowsQueryResponse,
    SchemaConflictError,
    TableNotFoundError,
    TablesPermissionError,
    create_table,
    delete_table,
    export_rows,
    infer_columns_from_file,
    get_import_job,
    get_table,
    list_tables,
    mutate_rows,
    query_rows,
    start_import,
    update_table,
)

router = APIRouter(prefix="/api/tables", tags=["tables"])


async def _read_uploaded_file(upload: UploadFile, *, max_size: int) -> bytes:
    total = 0
    chunks: list[bytes] = []
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{upload.filename or 'upload'}' exceeds max size of {max_size} bytes.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, (TableNotFoundError, ImportJobNotFoundError)):
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if isinstance(exc, SchemaConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if isinstance(exc, TablesPermissionError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if isinstance(exc, RowValidationError):
        detail: str | dict = str(exc)
        if exc.errors:
            detail = {
                "message": str(exc),
                "errors": exc.errors,
            }
        raise HTTPException(status_code=400, detail=detail) from exc

    if isinstance(exc, (ColumnValidationError, QueryValidationError, ImportFormatError)):
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    raise exc


@router.post("/infer-columns", response_model=InferColumnsResponse)
async def post_infer_columns(
    file: UploadFile = File(...),
    source_format: ImportFormat | None = Form(default=None),
    has_header: bool = Form(default=True),
    delimiter: str | None = Form(default=None),
) -> InferColumnsResponse:
    settings = get_settings()
    content = await _read_uploaded_file(file, max_size=settings.tables_max_file_size_bytes)

    try:
        return infer_columns_from_file(
            filename=file.filename,
            content=content,
            source_format=source_format,
            has_header=has_header,
            delimiter=(delimiter or None),
        )
    except Exception as exc:
        _raise_http_error(exc)


@router.post("", response_model=ReferenceTableDetail, status_code=status.HTTP_201_CREATED)
async def post_table(
    payload: ReferenceTableCreateInput,
    session: AsyncSession = Depends(get_db_session),
) -> ReferenceTableDetail:
    try:
        return await create_table(session, payload=payload)
    except Exception as exc:
        _raise_http_error(exc)


@router.get("", response_model=list[ReferenceTableSummary])
async def get_tables(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[ReferenceTableSummary]:
    return await list_tables(session, limit=limit, offset=offset)


@router.get("/{table_id}", response_model=ReferenceTableDetail)
async def get_table_by_id(
    table_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ReferenceTableDetail:
    try:
        return await get_table(session, table_id=table_id)
    except Exception as exc:
        _raise_http_error(exc)


@router.patch("/{table_id}", response_model=ReferenceTableDetail)
async def patch_table(
    table_id: str,
    payload: ReferenceTableUpdateInput,
    session: AsyncSession = Depends(get_db_session),
) -> ReferenceTableDetail:
    try:
        return await update_table(session, table_id=table_id, payload=payload)
    except Exception as exc:
        _raise_http_error(exc)


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_table(
    table_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    try:
        await delete_table(session, table_id=table_id)
    except Exception as exc:
        _raise_http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{table_id}/rows/query", response_model=RowsQueryResponse)
async def post_rows_query(
    table_id: str,
    payload: RowsQueryInput,
    session: AsyncSession = Depends(get_db_session),
) -> RowsQueryResponse:
    try:
        return await query_rows(session, table_id=table_id, payload=payload)
    except Exception as exc:
        _raise_http_error(exc)


@router.post("/{table_id}/rows/batch", response_model=RowsBatchResult)
async def post_rows_batch(
    table_id: str,
    payload: RowsBatchInput,
    session: AsyncSession = Depends(get_db_session),
) -> RowsBatchResult:
    try:
        return await mutate_rows(session, table_id=table_id, payload=payload)
    except Exception as exc:
        _raise_http_error(exc)


@router.post("/{table_id}/imports")
async def post_table_import(
    table_id: str,
    payload: ImportStartInput,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        return await start_import(session, table_id=table_id, payload=payload)
    except Exception as exc:
        _raise_http_error(exc)


@router.get("/{table_id}/imports/{job_id}")
async def get_table_import(
    table_id: str,
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        return await get_import_job(session, table_id=table_id, job_id=job_id)
    except Exception as exc:
        _raise_http_error(exc)


@router.post("/{table_id}/export")
async def post_table_export(
    table_id: str,
    payload: ExportInput,
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    try:
        exported = await export_rows(session, table_id=table_id, payload=payload)
    except Exception as exc:
        _raise_http_error(exc)

    return StreamingResponse(
        BytesIO(exported.content),
        media_type=exported.media_type,
        headers={"Content-Disposition": f'attachment; filename="{exported.filename}"'},
    )
