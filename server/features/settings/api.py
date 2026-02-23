from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_db_session

from .service import (
    activate_model_card,
    create_model_card,
    delete_model_card,
    list_model_cards,
    patch_company_profile,
    patch_model_card,
    patch_tool_settings,
    resolve_effective_company_profile,
    resolve_effective_tool_settings,
    reset_company_profile,
    reset_tool_settings,
    set_default_model_card,
    to_company_profile_response,
    to_tool_settings_response,
)
from .types import (
    CompanyProfilePatch,
    CompanyProfileResponse,
    ModelCardCreate,
    ModelCardPatch,
    ModelCardsResponse,
    ToolSettingsPatch,
    ToolSettingsResponse,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/models", response_model=ModelCardsResponse)
async def get_model_cards(
    session: AsyncSession = Depends(get_db_session),
) -> ModelCardsResponse:
    return await list_model_cards(session)


@router.post("/models", response_model=ModelCardsResponse)
async def create_model_card_route(
    payload: ModelCardCreate,
    session: AsyncSession = Depends(get_db_session),
) -> ModelCardsResponse:
    return await create_model_card(session, payload)


@router.patch("/models/{model_id}", response_model=ModelCardsResponse)
async def patch_model_card_route(
    model_id: str,
    payload: ModelCardPatch,
    session: AsyncSession = Depends(get_db_session),
) -> ModelCardsResponse:
    return await patch_model_card(session, model_id, payload)


@router.delete("/models/{model_id}", response_model=ModelCardsResponse)
async def delete_model_card_route(
    model_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ModelCardsResponse:
    return await delete_model_card(session, model_id)


@router.post("/models/{model_id}/activate", response_model=ModelCardsResponse)
async def activate_model_card_route(
    model_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ModelCardsResponse:
    return await activate_model_card(session, model_id)


@router.post("/models/{model_id}/default", response_model=ModelCardsResponse)
async def set_default_model_card_route(
    model_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ModelCardsResponse:
    return await set_default_model_card(session, model_id)


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
