from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_db_session

from .service import (
    patch_company_profile,
    patch_model_settings,
    patch_tool_settings,
    resolve_effective_company_profile,
    resolve_effective_model_settings,
    resolve_effective_tool_settings,
    reset_company_profile,
    reset_model_settings,
    reset_tool_settings,
    to_company_profile_response,
    to_model_settings_response,
    to_tool_settings_response,
)
from .types import (
    CompanyProfilePatch,
    CompanyProfileResponse,
    ModelSettingsPatch,
    ModelSettingsResponse,
    ToolSettingsPatch,
    ToolSettingsResponse,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/model", response_model=ModelSettingsResponse)
async def get_model_settings(
    session: AsyncSession = Depends(get_db_session),
) -> ModelSettingsResponse:
    settings = await resolve_effective_model_settings(session)
    return to_model_settings_response(settings)


@router.patch("/model", response_model=ModelSettingsResponse)
async def patch_model_settings_route(
    payload: ModelSettingsPatch,
    session: AsyncSession = Depends(get_db_session),
) -> ModelSettingsResponse:
    settings = await patch_model_settings(session, payload)
    return to_model_settings_response(settings)


@router.delete("/model")
async def delete_model_settings(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    reset = await reset_model_settings(session)
    return {"reset": reset}


@router.get("/tools", response_model=ToolSettingsResponse)
async def get_tool_settings(
    session: AsyncSession = Depends(get_db_session),
) -> ToolSettingsResponse:
    settings = await resolve_effective_tool_settings(session)
    return to_tool_settings_response(settings)


@router.patch("/tools", response_model=ToolSettingsResponse)
async def patch_tool_settings_route(
    payload: ToolSettingsPatch,
    session: AsyncSession = Depends(get_db_session),
) -> ToolSettingsResponse:
    settings = await patch_tool_settings(session, payload)
    return to_tool_settings_response(settings)


@router.delete("/tools")
async def delete_tool_settings(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    reset = await reset_tool_settings(session)
    return {"reset": reset}


@router.get("/company", response_model=CompanyProfileResponse)
async def get_company_profile(
    session: AsyncSession = Depends(get_db_session),
) -> CompanyProfileResponse:
    settings = await resolve_effective_company_profile(session)
    return to_company_profile_response(settings)


@router.patch("/company", response_model=CompanyProfileResponse)
async def patch_company_profile_route(
    payload: CompanyProfilePatch,
    session: AsyncSession = Depends(get_db_session),
) -> CompanyProfileResponse:
    settings = await patch_company_profile(session, payload)
    return to_company_profile_response(settings)


@router.delete("/company")
async def delete_company_profile(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    reset = await reset_company_profile(session)
    return {"reset": reset}
