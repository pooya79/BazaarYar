from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import ConversationReport
from server.features.shared.text_sanitize import log_sanitization_stats, sanitize_text

from . import repo
from .errors import ReportValidationError
from .types import ReportDetail, ReportSummary

_MAX_TITLE_LENGTH = 255
_MAX_PREVIEW_LENGTH = 180
_MAX_CONTENT_LENGTH = 20_000
logger = logging.getLogger(__name__)


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _derive_preview(content: str) -> str:
    collapsed = _collapse_whitespace(content)
    if len(collapsed) <= _MAX_PREVIEW_LENGTH:
        return collapsed
    return f"{collapsed[: _MAX_PREVIEW_LENGTH - 3].rstrip()}..."


def _validate_required_text(
    value: str | None,
    *,
    field_name: str,
    max_length: int,
) -> str:
    normalized, stats = sanitize_text(value or "", strip=True)
    log_sanitization_stats(logger, location=f"reports.validate_required_text.{field_name}", stats=stats)
    if not normalized:
        raise ReportValidationError(f"{field_name} cannot be empty.")
    if len(normalized) > max_length:
        raise ReportValidationError(f"{field_name} exceeds max length of {max_length}.")
    return normalized


def _validate_optional_preview(
    value: str | None,
    *,
    fallback_content: str,
) -> str:
    if value is None:
        return _derive_preview(fallback_content)
    normalized, stats = sanitize_text(value, strip=True)
    log_sanitization_stats(logger, location="reports.validate_optional_preview.preview_text", stats=stats)
    if not normalized:
        return _derive_preview(fallback_content)
    if len(normalized) > _MAX_PREVIEW_LENGTH:
        raise ReportValidationError(
            f"preview_text exceeds max length of {_MAX_PREVIEW_LENGTH}."
        )
    return normalized


def _normalize_source_conversation_id(value: str | UUID | None) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(value)
    except ValueError as exc:
        raise ReportValidationError("Invalid source_conversation_id.") from exc


def _to_summary(row: ConversationReport) -> ReportSummary:
    return ReportSummary(
        id=str(row.id),
        title=row.title,
        preview_text=row.preview_text,
        source_conversation_id=(
            str(row.source_conversation_id) if row.source_conversation_id else None
        ),
        enabled_for_agent=row.enabled_for_agent,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_detail(row: ConversationReport) -> ReportDetail:
    return ReportDetail(
        **_to_summary(row).model_dump(),
        content=row.content,
    )


async def create_report(
    session: AsyncSession,
    *,
    title: str,
    content: str,
    preview_text: str | None = None,
    enabled_for_agent: bool = True,
    source_conversation_id: str | UUID | None = None,
) -> ReportDetail:
    normalized_title = _validate_required_text(
        title,
        field_name="title",
        max_length=_MAX_TITLE_LENGTH,
    )
    normalized_content = _validate_required_text(
        content,
        field_name="content",
        max_length=_MAX_CONTENT_LENGTH,
    )
    normalized_preview = _validate_optional_preview(
        preview_text,
        fallback_content=normalized_content,
    )
    normalized_source_id = _normalize_source_conversation_id(source_conversation_id)

    row = await repo.create_report(
        session,
        title=normalized_title,
        preview_text=normalized_preview,
        content=normalized_content,
        source_conversation_id=normalized_source_id,
        enabled_for_agent=enabled_for_agent,
    )
    return _to_detail(row)


async def list_reports(
    session: AsyncSession,
    *,
    q: str = "",
    limit: int = 50,
    offset: int = 0,
    include_disabled: bool = False,
) -> list[ReportSummary]:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    rows = await repo.list_reports(
        session,
        q=q,
        limit=safe_limit,
        offset=safe_offset,
        include_disabled=include_disabled,
    )
    return [_to_summary(row) for row in rows]


async def get_report(
    session: AsyncSession,
    *,
    report_id: str | UUID,
    include_disabled: bool = True,
) -> ReportDetail:
    row = await repo.get_report(
        session,
        report_id=report_id,
        include_disabled=include_disabled,
    )
    return _to_detail(row)


async def update_report(
    session: AsyncSession,
    *,
    report_id: str | UUID,
    title: str | None = None,
    content: str | None = None,
    preview_text: str | None = None,
    enabled_for_agent: bool | None = None,
) -> ReportDetail:
    row = await repo.get_report(session, report_id=report_id, include_disabled=True)

    normalized_title: str | None = None
    if title is not None:
        normalized_title = _validate_required_text(
            title,
            field_name="title",
            max_length=_MAX_TITLE_LENGTH,
        )

    normalized_content: str | None = None
    candidate_content = row.content
    if content is not None:
        normalized_content = _validate_required_text(
            content,
            field_name="content",
            max_length=_MAX_CONTENT_LENGTH,
        )
        candidate_content = normalized_content

    normalized_preview: str | None = None
    if preview_text is not None:
        normalized_preview = _validate_optional_preview(
            preview_text,
            fallback_content=candidate_content,
        )

    updated = await repo.update_report(
        session,
        report=row,
        title=normalized_title,
        preview_text=normalized_preview,
        content=normalized_content,
        enabled_for_agent=enabled_for_agent,
    )
    return _to_detail(updated)


async def delete_report(
    session: AsyncSession,
    *,
    report_id: str | UUID,
) -> None:
    row = await repo.get_report(session, report_id=report_id, include_disabled=True)
    await repo.delete_report(session, report=row)
