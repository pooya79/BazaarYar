from __future__ import annotations

import logging
import re
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import PromptTemplate
from server.features.shared.text_sanitize import log_sanitization_stats, sanitize_text

from . import repo
from .errors import PromptValidationError
from .types import PromptDetail, PromptSummary

_MAX_NAME_LENGTH = 40
_MAX_DESCRIPTION_LENGTH = 180
_MAX_PROMPT_LENGTH = 20_000
_PROMPT_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,39}$")

logger = logging.getLogger(__name__)


def _to_summary(row: PromptTemplate) -> PromptSummary:
    return PromptSummary(
        id=str(row.id),
        name=row.name,
        description=row.description,
        prompt=row.prompt,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_detail(row: PromptTemplate) -> PromptDetail:
    return PromptDetail(**_to_summary(row).model_dump())


def _normalize_prompt_name(value: str | None) -> str:
    normalized, stats = sanitize_text(value or "", strip=True)
    log_sanitization_stats(logger, location="prompts.normalize.name", stats=stats)
    normalized = normalized.lstrip("\\").strip().lower()
    if not normalized:
        raise PromptValidationError("name cannot be empty.")
    if len(normalized) > _MAX_NAME_LENGTH:
        raise PromptValidationError(f"name exceeds max length of {_MAX_NAME_LENGTH}.")
    if not _PROMPT_NAME_PATTERN.fullmatch(normalized):
        raise PromptValidationError(
            "name must match ^[a-z0-9][a-z0-9_-]{1,39}$.",
        )
    return normalized


def _normalize_description(value: str | None) -> str:
    normalized, stats = sanitize_text(value or "", strip=True)
    log_sanitization_stats(logger, location="prompts.normalize.description", stats=stats)
    if len(normalized) > _MAX_DESCRIPTION_LENGTH:
        raise PromptValidationError(
            f"description exceeds max length of {_MAX_DESCRIPTION_LENGTH}.",
        )
    return normalized


def _normalize_prompt_body(value: str | None) -> str:
    normalized, stats = sanitize_text(value or "", strip=True)
    log_sanitization_stats(logger, location="prompts.normalize.prompt", stats=stats)
    if not normalized:
        raise PromptValidationError("prompt cannot be empty.")
    if len(normalized) > _MAX_PROMPT_LENGTH:
        raise PromptValidationError(f"prompt exceeds max length of {_MAX_PROMPT_LENGTH}.")
    return normalized


def _is_unique_name_violation(error: IntegrityError) -> bool:
    message = str(error).lower()
    return "uq_prompt_templates_name_lower" in message or "unique" in message


async def create_prompt(
    session: AsyncSession,
    *,
    name: str,
    description: str,
    prompt: str,
) -> PromptDetail:
    normalized_name = _normalize_prompt_name(name)
    normalized_description = _normalize_description(description)
    normalized_prompt = _normalize_prompt_body(prompt)

    existing = await repo.get_prompt_by_name(session, name=normalized_name)
    if existing is not None:
        raise PromptValidationError(f"Prompt '\\{normalized_name}' already exists.")

    try:
        row = await repo.create_prompt(
            session,
            name=normalized_name,
            description=normalized_description,
            prompt=normalized_prompt,
        )
    except IntegrityError as exc:
        if _is_unique_name_violation(exc):
            raise PromptValidationError(
                f"Prompt '\\{normalized_name}' already exists.",
            ) from exc
        raise

    return _to_detail(row)


async def list_prompts(
    session: AsyncSession,
    *,
    q: str = "",
    limit: int = 50,
    offset: int = 0,
) -> list[PromptSummary]:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    rows = await repo.list_prompts(
        session,
        q=q,
        limit=safe_limit,
        offset=safe_offset,
    )
    return [_to_summary(row) for row in rows]


async def get_prompt(
    session: AsyncSession,
    *,
    prompt_id: str | UUID,
) -> PromptDetail:
    row = await repo.get_prompt(session, prompt_id=prompt_id)
    return _to_detail(row)


async def update_prompt(
    session: AsyncSession,
    *,
    prompt_id: str | UUID,
    name: str | None = None,
    description: str | None = None,
    prompt: str | None = None,
) -> PromptDetail:
    row = await repo.get_prompt(session, prompt_id=prompt_id)

    normalized_name: str | None = None
    if name is not None:
        normalized_name = _normalize_prompt_name(name)
        existing = await repo.get_prompt_by_name(
            session,
            name=normalized_name,
            exclude_prompt_id=row.id,
        )
        if existing is not None:
            raise PromptValidationError(f"Prompt '\\{normalized_name}' already exists.")

    normalized_description: str | None = None
    if description is not None:
        normalized_description = _normalize_description(description)

    normalized_prompt: str | None = None
    if prompt is not None:
        normalized_prompt = _normalize_prompt_body(prompt)

    try:
        updated = await repo.update_prompt(
            session,
            prompt_row=row,
            name=normalized_name,
            description=normalized_description,
            prompt=normalized_prompt,
        )
    except IntegrityError as exc:
        if normalized_name and _is_unique_name_violation(exc):
            raise PromptValidationError(
                f"Prompt '\\{normalized_name}' already exists.",
            ) from exc
        raise

    return _to_detail(updated)


async def delete_prompt(
    session: AsyncSession,
    *,
    prompt_id: str | UUID,
) -> None:
    row = await repo.get_prompt(session, prompt_id=prompt_id)
    await repo.delete_prompt(session, prompt_row=row)

