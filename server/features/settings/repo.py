from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import AgentModelSettings

GLOBAL_SINGLETON_KEY = "global"


async def get_global_model_settings(session: AsyncSession) -> AgentModelSettings | None:
    stmt = select(AgentModelSettings).where(AgentModelSettings.singleton_key == GLOBAL_SINGLETON_KEY)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_global_model_settings(
    session: AsyncSession,
    *,
    model_name: str,
    api_key: str,
    base_url: str,
    temperature: float,
    reasoning_effort: str,
    reasoning_enabled: bool,
) -> AgentModelSettings:
    row = await get_global_model_settings(session)
    if row is None:
        row = AgentModelSettings(
            singleton_key=GLOBAL_SINGLETON_KEY,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            reasoning_enabled=reasoning_enabled,
        )
        session.add(row)
    else:
        row.model_name = model_name
        row.api_key = api_key
        row.base_url = base_url
        row.temperature = temperature
        row.reasoning_effort = reasoning_effort
        row.reasoning_enabled = reasoning_enabled

    await session.commit()
    await session.refresh(row)
    return row


async def delete_global_model_settings(session: AsyncSession) -> bool:
    row = await get_global_model_settings(session)
    if row is None:
        return False

    await session.delete(row)
    await session.commit()
    return True
