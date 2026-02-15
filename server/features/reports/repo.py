from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import ConversationReport

from .errors import ReportNotFoundError, ReportValidationError


def _to_uuid(value: UUID | str, *, field_name: str) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(value)
    except ValueError as exc:
        raise ReportValidationError(f"Invalid {field_name}.") from exc


async def create_report(
    session: AsyncSession,
    *,
    title: str,
    preview_text: str,
    content: str,
    source_conversation_id: UUID | None,
    enabled_for_agent: bool,
) -> ConversationReport:
    report = ConversationReport(
        title=title,
        preview_text=preview_text,
        content=content,
        source_conversation_id=source_conversation_id,
        enabled_for_agent=enabled_for_agent,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def list_reports(
    session: AsyncSession,
    *,
    q: str,
    limit: int,
    offset: int,
    include_disabled: bool,
) -> list[ConversationReport]:
    stmt = select(ConversationReport)
    if not include_disabled:
        stmt = stmt.where(ConversationReport.enabled_for_agent.is_(True))

    clean_query = q.strip()
    if clean_query:
        like = f"%{clean_query}%"
        stmt = stmt.where(
            or_(
                ConversationReport.title.ilike(like),
                ConversationReport.preview_text.ilike(like),
                ConversationReport.content.ilike(like),
            )
        )

    stmt = (
        stmt.order_by(ConversationReport.created_at.desc(), ConversationReport.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_report(
    session: AsyncSession,
    *,
    report_id: UUID | str,
    include_disabled: bool = True,
) -> ConversationReport:
    report_uuid = _to_uuid(report_id, field_name="report_id")
    stmt = select(ConversationReport).where(ConversationReport.id == report_uuid)
    if not include_disabled:
        stmt = stmt.where(ConversationReport.enabled_for_agent.is_(True))

    report = (await session.execute(stmt)).scalar_one_or_none()
    if report is None:
        raise ReportNotFoundError(f"Report '{report_id}' was not found.")
    return report


async def update_report(
    session: AsyncSession,
    *,
    report: ConversationReport,
    title: str | None = None,
    preview_text: str | None = None,
    content: str | None = None,
    enabled_for_agent: bool | None = None,
) -> ConversationReport:
    if title is not None:
        report.title = title
    if preview_text is not None:
        report.preview_text = preview_text
    if content is not None:
        report.content = content
    if enabled_for_agent is not None:
        report.enabled_for_agent = enabled_for_agent
    await session.commit()
    await session.refresh(report)
    return report


async def delete_report(
    session: AsyncSession,
    *,
    report: ConversationReport,
) -> None:
    await session.delete(report)
    await session.commit()
