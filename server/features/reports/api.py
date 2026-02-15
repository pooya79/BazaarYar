from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_db_session

from .errors import ReportNotFoundError, ReportValidationError
from .service import create_report, delete_report, get_report, list_reports, update_report
from .types import ReportCreateInput, ReportDetail, ReportSummary, ReportUpdateInput

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, ReportNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ReportValidationError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=list[ReportSummary])
async def get_reports(
    q: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_disabled: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
) -> list[ReportSummary]:
    return await list_reports(
        session,
        q=q,
        limit=limit,
        offset=offset,
        include_disabled=include_disabled,
    )


@router.post("", response_model=ReportDetail, status_code=status.HTTP_201_CREATED)
async def post_report(
    payload: ReportCreateInput,
    session: AsyncSession = Depends(get_db_session),
) -> ReportDetail:
    try:
        return await create_report(
            session,
            title=payload.title,
            content=payload.content,
            preview_text=payload.preview_text,
            enabled_for_agent=payload.enabled_for_agent,
            source_conversation_id=payload.source_conversation_id,
        )
    except Exception as exc:
        _raise_http_error(exc)


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report_by_id(
    report_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ReportDetail:
    try:
        return await get_report(session, report_id=report_id, include_disabled=True)
    except Exception as exc:
        _raise_http_error(exc)


@router.patch("/{report_id}", response_model=ReportDetail)
async def patch_report(
    report_id: str,
    payload: ReportUpdateInput,
    session: AsyncSession = Depends(get_db_session),
) -> ReportDetail:
    try:
        return await update_report(
            session,
            report_id=report_id,
            title=payload.title,
            content=payload.content,
            preview_text=payload.preview_text,
            enabled_for_agent=payload.enabled_for_agent,
        )
    except Exception as exc:
        _raise_http_error(exc)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_report(
    report_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    try:
        await delete_report(session, report_id=report_id)
    except Exception as exc:
        _raise_http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
