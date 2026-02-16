from __future__ import annotations

import logging
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import get_settings
from server.features.shared.text_sanitize import log_sanitization_stats, sanitize_text

from . import repo
from .types import (
    CompanyProfilePatch,
    CompanyProfileResolved,
    CompanyProfileResponse,
    ModelSettingsPatch,
    ModelSettingsResolved,
    ModelSettingsResponse,
    ReasoningEffort,
)

logger = logging.getLogger(__name__)


def default_model_settings_from_env() -> ModelSettingsResolved:
    settings = get_settings()
    return ModelSettingsResolved(
        model_name=settings.openailike_model,
        api_key=settings.openailike_api_key,
        base_url=settings.openailike_base_url,
        temperature=settings.openailike_temperature,
        reasoning_effort=settings.openailike_reasoning_effort,
        reasoning_enabled=settings.openailike_reasoning_enabled,
        source="environment_defaults",
    )


async def resolve_effective_model_settings(session: AsyncSession) -> ModelSettingsResolved:
    row = await repo.get_global_model_settings(session)
    if row is None:
        return default_model_settings_from_env()

    return ModelSettingsResolved(
        model_name=row.model_name,
        api_key=row.api_key,
        base_url=row.base_url,
        temperature=row.temperature,
        reasoning_effort=cast(ReasoningEffort, row.reasoning_effort),
        reasoning_enabled=row.reasoning_enabled,
        source="database",
    )


def default_company_profile() -> CompanyProfileResolved:
    return CompanyProfileResolved(
        name="",
        description="",
        enabled=True,
        source="defaults",
    )


async def resolve_effective_company_profile(session: AsyncSession) -> CompanyProfileResolved:
    row = await repo.get_global_company_profile(session)
    if row is None:
        return default_company_profile()

    return CompanyProfileResolved(
        name=row.name,
        description=row.description,
        enabled=row.enabled,
        source="database",
    )


def _preview_api_key(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) <= 8:
        return "*" * len(cleaned)
    return f"{cleaned[:4]}...{cleaned[-4:]}"


def to_model_settings_response(settings: ModelSettingsResolved) -> ModelSettingsResponse:
    preview = _preview_api_key(settings.api_key)
    return ModelSettingsResponse(
        model_name=settings.model_name,
        base_url=settings.base_url,
        temperature=settings.temperature,
        reasoning_effort=settings.reasoning_effort,
        reasoning_enabled=settings.reasoning_enabled,
        has_api_key=bool(settings.api_key.strip()),
        api_key_preview=preview,
        source=settings.source,
    )


def to_company_profile_response(settings: CompanyProfileResolved) -> CompanyProfileResponse:
    return CompanyProfileResponse(
        name=settings.name,
        description=settings.description,
        enabled=settings.enabled,
        source=settings.source,
    )


async def patch_model_settings(
    session: AsyncSession,
    patch_payload: ModelSettingsPatch,
) -> ModelSettingsResolved:
    current = await resolve_effective_model_settings(session)
    patch_data = patch_payload.model_dump(exclude_unset=True)
    if not patch_data:
        return current

    if "model_name" in patch_data:
        candidate_model_name, name_stats = sanitize_text(
            str(patch_data["model_name"] or ""),
            strip=True,
        )
        log_sanitization_stats(
            logger,
            location="settings.patch_model_settings.model_name",
            stats=name_stats,
        )
        model_name = candidate_model_name or current.model_name
    else:
        model_name = current.model_name
    model_name, normalized_name_stats = sanitize_text(model_name, strip=True)
    log_sanitization_stats(
        logger,
        location="settings.patch_model_settings.model_name.normalized",
        stats=normalized_name_stats,
    )
    if not model_name:
        model_name = current.model_name
    api_key_raw = patch_data.get("api_key", current.api_key)
    base_url_raw = patch_data.get("base_url", current.base_url)
    if isinstance(api_key_raw, str):
        api_key, api_key_stats = sanitize_text(api_key_raw, strip=False)
        log_sanitization_stats(
            logger,
            location="settings.patch_model_settings.api_key",
            stats=api_key_stats,
        )
    else:
        api_key = api_key_raw
    if isinstance(base_url_raw, str):
        base_url, base_url_stats = sanitize_text(base_url_raw, strip=False)
        log_sanitization_stats(
            logger,
            location="settings.patch_model_settings.base_url",
            stats=base_url_stats,
        )
    else:
        base_url = base_url_raw
    temperature = float(patch_data.get("temperature", current.temperature))
    reasoning_effort = cast(
        ReasoningEffort,
        patch_data.get("reasoning_effort", current.reasoning_effort),
    )
    reasoning_enabled = bool(patch_data.get("reasoning_enabled", current.reasoning_enabled))

    row = await repo.upsert_global_model_settings(
        session,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        reasoning_effort=reasoning_effort,
        reasoning_enabled=reasoning_enabled,
    )
    return ModelSettingsResolved(
        model_name=row.model_name,
        api_key=row.api_key,
        base_url=row.base_url,
        temperature=row.temperature,
        reasoning_effort=cast(ReasoningEffort, row.reasoning_effort),
        reasoning_enabled=row.reasoning_enabled,
        source="database",
    )


async def reset_model_settings(session: AsyncSession) -> bool:
    return await repo.delete_global_model_settings(session)


async def patch_company_profile(
    session: AsyncSession,
    patch_payload: CompanyProfilePatch,
) -> CompanyProfileResolved:
    current = await resolve_effective_company_profile(session)
    patch_data = patch_payload.model_dump(exclude_unset=True)
    if not patch_data:
        return current

    if "name" in patch_data:
        name, name_stats = sanitize_text(str(patch_data["name"] or ""), strip=True)
        log_sanitization_stats(
            logger,
            location="settings.patch_company_profile.name",
            stats=name_stats,
        )
    else:
        name = current.name
    name, normalized_name_stats = sanitize_text(name, strip=True)
    log_sanitization_stats(
        logger,
        location="settings.patch_company_profile.name.normalized",
        stats=normalized_name_stats,
    )

    if "description" in patch_data:
        description, description_stats = sanitize_text(
            str(patch_data["description"] or ""),
            strip=True,
        )
        log_sanitization_stats(
            logger,
            location="settings.patch_company_profile.description",
            stats=description_stats,
        )
    else:
        description = current.description
    description, normalized_description_stats = sanitize_text(description, strip=True)
    log_sanitization_stats(
        logger,
        location="settings.patch_company_profile.description.normalized",
        stats=normalized_description_stats,
    )

    enabled = bool(patch_data.get("enabled", current.enabled))
    row = await repo.upsert_global_company_profile(
        session,
        name=name,
        description=description,
        enabled=enabled,
    )
    return CompanyProfileResolved(
        name=row.name,
        description=row.description,
        enabled=row.enabled,
        source="database",
    )


async def reset_company_profile(session: AsyncSession) -> bool:
    return await repo.delete_global_company_profile(session)
