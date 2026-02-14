from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_db_session

from .service import (
    patch_model_settings,
    resolve_effective_model_settings,
    reset_model_settings,
    to_model_settings_response,
)
from .types import ModelSettingsPatch, ModelSettingsResponse

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
