from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import PromptTemplate
from server.features.shared.text_sanitize import log_sanitization_stats, sanitize_text

from .errors import PromptNotFoundError, PromptValidationError

logger = logging.getLogger(__name__)


def _to_uuid(value: UUID | str, *, field_name: str) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(value)
    except ValueError as exc:
        raise PromptValidationError(f"Invalid {field_name}.") from exc


async def create_prompt(
    session: AsyncSession,
    *,
    name: str,
    description: str,
    prompt: str,
) -> PromptTemplate:
    clean_name, name_stats = sanitize_text(name, strip=False)
    clean_description, description_stats = sanitize_text(description, strip=False)
    clean_prompt, prompt_stats = sanitize_text(prompt, strip=False)
    log_sanitization_stats(logger, location="prompts.create_prompt.name", stats=name_stats)
    log_sanitization_stats(
        logger,
        location="prompts.create_prompt.description",
        stats=description_stats,
    )
    log_sanitization_stats(
        logger,
        location="prompts.create_prompt.prompt",
        stats=prompt_stats,
    )
    row = PromptTemplate(
        name=clean_name,
        description=clean_description,
        prompt=clean_prompt,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_prompts(
    session: AsyncSession,
    *,
    q: str,
    limit: int,
    offset: int,
) -> list[PromptTemplate]:
    stmt = select(PromptTemplate)

    clean_query, query_stats = sanitize_text(q, strip=True)
    log_sanitization_stats(logger, location="prompts.list_prompts.query", stats=query_stats)
    if clean_query:
        stmt = stmt.where(PromptTemplate.name.ilike(f"%{clean_query}%"))

    stmt = (
        stmt.order_by(PromptTemplate.created_at.desc(), PromptTemplate.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_prompt(
    session: AsyncSession,
    *,
    prompt_id: UUID | str,
) -> PromptTemplate:
    prompt_uuid = _to_uuid(prompt_id, field_name="prompt_id")
    row = (
        await session.execute(
            select(PromptTemplate).where(PromptTemplate.id == prompt_uuid)
        )
    ).scalar_one_or_none()
    if row is None:
        raise PromptNotFoundError(f"Prompt '{prompt_id}' was not found.")
    return row


async def get_prompt_by_name(
    session: AsyncSession,
    *,
    name: str,
    exclude_prompt_id: UUID | str | None = None,
) -> PromptTemplate | None:
    stmt = select(PromptTemplate).where(func.lower(PromptTemplate.name) == name.lower())
    if exclude_prompt_id is not None:
        excluded_uuid = _to_uuid(exclude_prompt_id, field_name="exclude_prompt_id")
        stmt = stmt.where(PromptTemplate.id != excluded_uuid)
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_prompt(
    session: AsyncSession,
    *,
    prompt_row: PromptTemplate,
    name: str | None = None,
    description: str | None = None,
    prompt: str | None = None,
) -> PromptTemplate:
    if name is not None:
        clean_name, name_stats = sanitize_text(name, strip=False)
        log_sanitization_stats(logger, location="prompts.update_prompt.name", stats=name_stats)
        prompt_row.name = clean_name
    if description is not None:
        clean_description, description_stats = sanitize_text(description, strip=False)
        log_sanitization_stats(
            logger,
            location="prompts.update_prompt.description",
            stats=description_stats,
        )
        prompt_row.description = clean_description
    if prompt is not None:
        clean_prompt, prompt_stats = sanitize_text(prompt, strip=False)
        log_sanitization_stats(
            logger,
            location="prompts.update_prompt.prompt",
            stats=prompt_stats,
        )
        prompt_row.prompt = clean_prompt
    await session.commit()
    await session.refresh(prompt_row)
    return prompt_row


async def delete_prompt(
    session: AsyncSession,
    *,
    prompt_row: PromptTemplate,
) -> None:
    await session.delete(prompt_row)
    await session.commit()

