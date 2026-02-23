from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_db_session

from .errors import PromptNotFoundError, PromptValidationError
from .service import create_prompt, delete_prompt, get_prompt, list_prompts, update_prompt
from .types import PromptCreateInput, PromptDetail, PromptSummary, PromptUpdateInput

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, PromptNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, PromptValidationError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=list[PromptSummary])
async def get_prompts(
    q: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[PromptSummary]:
    return await list_prompts(
        session,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=PromptDetail, status_code=status.HTTP_201_CREATED)
async def post_prompt(
    payload: PromptCreateInput,
    session: AsyncSession = Depends(get_db_session),
) -> PromptDetail:
    try:
        return await create_prompt(
            session,
            name=payload.name,
            description=payload.description,
            prompt=payload.prompt,
        )
    except Exception as exc:
        _raise_http_error(exc)


@router.get("/{prompt_id}", response_model=PromptDetail)
async def get_prompt_by_id(
    prompt_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> PromptDetail:
    try:
        return await get_prompt(session, prompt_id=prompt_id)
    except Exception as exc:
        _raise_http_error(exc)


@router.patch("/{prompt_id}", response_model=PromptDetail)
async def patch_prompt(
    prompt_id: str,
    payload: PromptUpdateInput,
    session: AsyncSession = Depends(get_db_session),
) -> PromptDetail:
    try:
        return await update_prompt(
            session,
            prompt_id=prompt_id,
            name=payload.name,
            description=payload.description,
            prompt=payload.prompt,
        )
    except Exception as exc:
        _raise_http_error(exc)


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_prompt(
    prompt_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    try:
        await delete_prompt(session, prompt_id=prompt_id)
    except Exception as exc:
        _raise_http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

