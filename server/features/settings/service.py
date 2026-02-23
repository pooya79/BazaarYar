from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import get_settings
from server.db.models import AgentModelSettings
from server.features.agent.runtime import (
    resolve_tool_groups,
    tool_default_enabled_map,
    tool_registry_keys,
)
from server.features.shared.text_sanitize import log_sanitization_stats, sanitize_text

from . import repo
from .types import (
    CompanyProfilePatch,
    CompanyProfileResolved,
    CompanyProfileResponse,
    ModelCardCreate,
    ModelCardPatch,
    ModelCardResponse,
    ModelCardsResponse,
    ModelSettingsResolved,
    ReasoningEffort,
    ToolCatalogGroup,
    ToolCatalogTool,
    ToolSettingsPatch,
    ToolSettingsResolved,
    ToolSettingsResponse,
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


def _preview_api_key(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) <= 8:
        return "*" * len(cleaned)
    return f"{cleaned[:4]}...{cleaned[-4:]}"


def _resolve_from_row(row: AgentModelSettings) -> ModelSettingsResolved:
    return ModelSettingsResolved(
        model_name=row.model_name,
        api_key=row.api_key,
        base_url=row.base_url,
        temperature=row.temperature,
        reasoning_effort=cast(ReasoningEffort, row.reasoning_effort),
        reasoning_enabled=row.reasoning_enabled,
        source="database",
    )


def _to_model_card_response(row: AgentModelSettings) -> ModelCardResponse:
    return ModelCardResponse(
        id=str(row.id),
        display_name=row.display_name,
        model_name=row.model_name,
        base_url=row.base_url,
        temperature=row.temperature,
        reasoning_effort=cast(ReasoningEffort, row.reasoning_effort),
        reasoning_enabled=row.reasoning_enabled,
        has_api_key=bool(row.api_key.strip()),
        api_key_preview=_preview_api_key(row.api_key),
        is_default=row.is_default,
        is_active=row.is_active,
    )


def _parse_model_id(model_id: str, *, field_name: str = "model_id") -> UUID:
    try:
        return UUID(model_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {field_name}.") from exc


def _sanitize_display_name(value: str, *, location: str) -> str:
    normalized, stats = sanitize_text(value, strip=True)
    log_sanitization_stats(logger, location=location, stats=stats)
    if not normalized:
        raise HTTPException(status_code=422, detail="display_name cannot be empty.")
    return normalized


def _sanitize_model_name(value: str, *, location: str) -> str:
    normalized, stats = sanitize_text(value, strip=True)
    log_sanitization_stats(logger, location=location, stats=stats)
    if not normalized:
        raise HTTPException(status_code=422, detail="model_name cannot be empty.")
    return normalized


def _sanitize_optional_secret(value: str | None, *, location: str) -> str:
    raw = value if isinstance(value, str) else ""
    normalized, stats = sanitize_text(raw, strip=False)
    log_sanitization_stats(logger, location=location, stats=stats)
    return normalized


def _sanitize_optional_value(value: str | None, *, location: str) -> str:
    raw = value if isinstance(value, str) else ""
    normalized, stats = sanitize_text(raw, strip=False)
    log_sanitization_stats(logger, location=location, stats=stats)
    return normalized


async def _model_cards_response(session: AsyncSession) -> ModelCardsResponse:
    rows = await repo.list_model_cards(session)
    active_row = next((row for row in rows if row.is_active), None)
    default_row = next((row for row in rows if row.is_default), None)
    return ModelCardsResponse(
        items=[_to_model_card_response(row) for row in rows],
        active_model_id=str(active_row.id) if active_row else None,
        default_model_id=str(default_row.id) if default_row else None,
    )


async def _ensure_single_default_and_active(
    session: AsyncSession,
    *,
    preferred_default_id: UUID | None = None,
    preferred_active_id: UUID | None = None,
) -> None:
    rows = await repo.list_model_cards(session)
    if not rows:
        return

    default_candidate = None
    if preferred_default_id is not None:
        default_candidate = next((row for row in rows if row.id == preferred_default_id), None)
    if default_candidate is None:
        default_candidate = next((row for row in rows if row.is_default), None) or rows[0]

    current_defaults = [row for row in rows if row.is_default]
    if len(current_defaults) != 1 or current_defaults[0].id != default_candidate.id:
        await repo.set_default_model_card(session, default_candidate.id)
        rows = await repo.list_model_cards(session)
        default_candidate = next((row for row in rows if row.id == default_candidate.id), default_candidate)

    active_candidate = None
    if preferred_active_id is not None:
        active_candidate = next((row for row in rows if row.id == preferred_active_id), None)
    if active_candidate is None:
        active_candidate = next((row for row in rows if row.is_active), None)
    if active_candidate is None:
        active_candidate = next((row for row in rows if row.id == default_candidate.id), None) or rows[0]

    current_actives = [row for row in rows if row.is_active]
    if len(current_actives) != 1 or current_actives[0].id != active_candidate.id:
        await repo.set_active_model_card(session, active_candidate.id)


async def list_model_cards(session: AsyncSession) -> ModelCardsResponse:
    await _ensure_single_default_and_active(session)
    return await _model_cards_response(session)


async def create_model_card(
    session: AsyncSession,
    payload: ModelCardCreate,
) -> ModelCardsResponse:
    display_name = _sanitize_display_name(
        payload.display_name,
        location="settings.create_model_card.display_name",
    )
    model_name = _sanitize_model_name(
        payload.model_name,
        location="settings.create_model_card.model_name",
    )
    api_key = _sanitize_optional_secret(
        payload.api_key,
        location="settings.create_model_card.api_key",
    )
    base_url = _sanitize_optional_value(
        payload.base_url,
        location="settings.create_model_card.base_url",
    )

    row = await repo.create_model_card(
        session,
        display_name=display_name,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=payload.temperature,
        reasoning_effort=payload.reasoning_effort,
        reasoning_enabled=payload.reasoning_enabled,
        is_default=payload.is_default,
        is_active=payload.is_active,
    )
    await _ensure_single_default_and_active(
        session,
        preferred_default_id=row.id if payload.is_default else None,
        preferred_active_id=row.id if payload.is_active else None,
    )
    return await _model_cards_response(session)


async def patch_model_card(
    session: AsyncSession,
    model_id: str,
    payload: ModelCardPatch,
) -> ModelCardsResponse:
    row_id = _parse_model_id(model_id)
    row = await repo.get_model_card(session, row_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model card '{model_id}' was not found.")

    patch_data = payload.model_dump(exclude_unset=True)
    if not patch_data:
        return await _model_cards_response(session)

    display_name = (
        _sanitize_display_name(
            str(patch_data["display_name"] or ""),
            location="settings.patch_model_card.display_name",
        )
        if "display_name" in patch_data
        else row.display_name
    )
    model_name = (
        _sanitize_model_name(
            str(patch_data["model_name"] or ""),
            location="settings.patch_model_card.model_name",
        )
        if "model_name" in patch_data
        else row.model_name
    )

    if "api_key" in patch_data:
        api_key = _sanitize_optional_secret(
            payload.api_key,
            location="settings.patch_model_card.api_key",
        )
    else:
        api_key = row.api_key

    if "base_url" in patch_data:
        base_url = _sanitize_optional_value(
            payload.base_url,
            location="settings.patch_model_card.base_url",
        )
    else:
        base_url = row.base_url

    temperature = float(patch_data.get("temperature", row.temperature))
    reasoning_effort = cast(
        ReasoningEffort,
        patch_data.get("reasoning_effort", row.reasoning_effort),
    )
    reasoning_enabled = bool(patch_data.get("reasoning_enabled", row.reasoning_enabled))
    is_default = bool(patch_data.get("is_default", row.is_default))
    is_active = bool(patch_data.get("is_active", row.is_active))

    await repo.update_model_card(
        session,
        row,
        display_name=display_name,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        reasoning_effort=reasoning_effort,
        reasoning_enabled=reasoning_enabled,
        is_default=is_default,
        is_active=is_active,
    )

    await _ensure_single_default_and_active(
        session,
        preferred_default_id=row.id if patch_data.get("is_default") is True else None,
        preferred_active_id=row.id if patch_data.get("is_active") is True else None,
    )
    return await _model_cards_response(session)


async def delete_model_card(session: AsyncSession, model_id: str) -> ModelCardsResponse:
    row_id = _parse_model_id(model_id)
    rows = await repo.list_model_cards(session)
    if len(rows) <= 1:
        raise HTTPException(status_code=400, detail="At least one model card is required.")

    deleted = await repo.delete_model_card(session, row_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Model card '{model_id}' was not found.")

    await _ensure_single_default_and_active(session)
    return await _model_cards_response(session)


async def activate_model_card(session: AsyncSession, model_id: str) -> ModelCardsResponse:
    row_id = _parse_model_id(model_id)
    row = await repo.set_active_model_card(session, row_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model card '{model_id}' was not found.")
    await _ensure_single_default_and_active(session)
    return await _model_cards_response(session)


async def set_default_model_card(session: AsyncSession, model_id: str) -> ModelCardsResponse:
    row_id = _parse_model_id(model_id)
    row = await repo.set_default_model_card(session, row_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model card '{model_id}' was not found.")
    await _ensure_single_default_and_active(session)
    return await _model_cards_response(session)


async def resolve_effective_model_settings(
    session: AsyncSession,
    *,
    model_id: str | None = None,
    activate_selected: bool = False,
) -> ModelSettingsResolved:
    if model_id:
        selected_id = _parse_model_id(model_id, field_name="model_id")
        selected_row = await repo.get_model_card(session, selected_id)
        if selected_row is None:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown model_id '{model_id}'.",
            )
        if activate_selected:
            activated = await repo.set_active_model_card(session, selected_id)
            if activated is not None:
                selected_row = activated
        return _resolve_from_row(selected_row)

    active_row = await repo.get_active_model_card(session)
    if active_row is not None:
        return _resolve_from_row(active_row)

    default_row = await repo.get_default_model_card(session)
    if default_row is not None:
        return _resolve_from_row(default_row)

    return default_model_settings_from_env()


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


def default_tool_settings() -> ToolSettingsResolved:
    return ToolSettingsResolved(
        tool_overrides={},
        source="defaults",
    )


def _normalize_tool_overrides(
    value: object,
) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, bool] = {}
    for key, item in value.items():
        if isinstance(key, str) and isinstance(item, bool):
            normalized[key] = item
    return normalized


async def resolve_effective_tool_settings(session: AsyncSession) -> ToolSettingsResolved:
    row = await repo.get_global_tool_settings(session)
    if row is None:
        return default_tool_settings()

    known_keys = tool_registry_keys()
    filtered_overrides = {
        key: value
        for key, value in _normalize_tool_overrides(row.tool_overrides_json).items()
        if key in known_keys
    }

    return ToolSettingsResolved(
        tool_overrides=filtered_overrides,
        source="database",
    )


def to_company_profile_response(settings: CompanyProfileResolved) -> CompanyProfileResponse:
    return CompanyProfileResponse(
        name=settings.name,
        description=settings.description,
        enabled=settings.enabled,
        source=settings.source,
    )


def to_tool_settings_response(settings: ToolSettingsResolved) -> ToolSettingsResponse:
    resolved_groups = resolve_tool_groups(settings.tool_overrides)
    groups: list[ToolCatalogGroup] = []
    for group in resolved_groups:
        groups.append(
            ToolCatalogGroup(
                key=group.key,
                label=group.label,
                enabled=group.enabled,
                tools=[
                    ToolCatalogTool(
                        key=tool.key,
                        label=tool.label,
                        description=tool.description,
                        default_enabled=tool.default_enabled,
                        available=tool.available,
                        unavailable_reason=tool.unavailable_reason,
                        enabled=tool.enabled,
                    )
                    for tool in group.tools
                ],
            )
        )

    known_keys = tool_registry_keys()
    filtered_overrides = {
        key: value
        for key, value in settings.tool_overrides.items()
        if key in known_keys
    }

    return ToolSettingsResponse(
        groups=groups,
        tool_overrides=filtered_overrides,
        source=settings.source,
    )


async def patch_tool_settings(
    session: AsyncSession,
    patch_payload: ToolSettingsPatch,
) -> ToolSettingsResolved:
    current = await resolve_effective_tool_settings(session)
    patch_data = patch_payload.model_dump(exclude_unset=True)
    if not patch_data:
        return current

    incoming = patch_data.get("tool_overrides", {})
    if not isinstance(incoming, dict):
        incoming = {}

    known_keys = tool_registry_keys()
    unknown_keys = [key for key in incoming if key not in known_keys]
    if unknown_keys:
        sorted_keys = ", ".join(sorted(unknown_keys))
        raise HTTPException(
            status_code=422,
            detail=f"Unknown tool key(s): {sorted_keys}",
        )

    merged = dict(current.tool_overrides)
    for key, value in incoming.items():
        if isinstance(value, bool):
            merged[key] = value

    defaults = tool_default_enabled_map()
    overrides_for_storage = {
        key: value
        for key, value in merged.items()
        if key in known_keys and value != defaults.get(key, True)
    }

    row = await repo.upsert_global_tool_settings(
        session,
        tool_overrides_json=overrides_for_storage,
    )
    return ToolSettingsResolved(
        tool_overrides=_normalize_tool_overrides(row.tool_overrides_json),
        source="database",
    )


async def reset_tool_settings(session: AsyncSession) -> bool:
    return await repo.delete_global_tool_settings(session)


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
