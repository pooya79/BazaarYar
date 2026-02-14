from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import get_settings

from . import repo
from .types import ModelSettingsPatch, ModelSettingsResolved, ModelSettingsResponse, ReasoningEffort


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


async def patch_model_settings(
    session: AsyncSession,
    patch_payload: ModelSettingsPatch,
) -> ModelSettingsResolved:
    current = await resolve_effective_model_settings(session)
    patch_data = patch_payload.model_dump(exclude_unset=True)
    if not patch_data:
        return current

    if "model_name" in patch_data:
        candidate_model_name = str(patch_data["model_name"] or "").strip()
        model_name = candidate_model_name or current.model_name
    else:
        model_name = current.model_name
    api_key = patch_data.get("api_key", current.api_key)
    base_url = patch_data.get("base_url", current.base_url)
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
