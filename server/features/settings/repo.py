from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import AgentCompanyProfile, AgentModelSettings

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


async def get_global_company_profile(session: AsyncSession) -> AgentCompanyProfile | None:
    stmt = select(AgentCompanyProfile).where(AgentCompanyProfile.singleton_key == GLOBAL_SINGLETON_KEY)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_global_company_profile(
    session: AsyncSession,
    *,
    name: str,
    description: str,
    enabled: bool,
) -> AgentCompanyProfile:
    row = await get_global_company_profile(session)
    if row is None:
        row = AgentCompanyProfile(
            singleton_key=GLOBAL_SINGLETON_KEY,
            name=name,
            description=description,
            enabled=enabled,
        )
        session.add(row)
    else:
        row.name = name
        row.description = description
        row.enabled = enabled

    await session.commit()
    await session.refresh(row)
    return row


async def delete_global_company_profile(session: AsyncSession) -> bool:
    row = await get_global_company_profile(session)
    if row is None:
        return False

    await session.delete(row)
    await session.commit()
    return True
