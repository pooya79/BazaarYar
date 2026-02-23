from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import AgentCompanyProfile, AgentModelSettings, AgentToolSettings

GLOBAL_SINGLETON_KEY = "global"


async def list_model_cards(session: AsyncSession) -> list[AgentModelSettings]:
    stmt = select(AgentModelSettings).order_by(
        AgentModelSettings.created_at.asc(),
        AgentModelSettings.id.asc(),
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_model_card(
    session: AsyncSession,
    model_id: UUID,
) -> AgentModelSettings | None:
    return await session.get(AgentModelSettings, model_id)


async def get_active_model_card(session: AsyncSession) -> AgentModelSettings | None:
    stmt = (
        select(AgentModelSettings)
        .where(AgentModelSettings.is_active.is_(True))
        .order_by(AgentModelSettings.created_at.asc(), AgentModelSettings.id.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_default_model_card(session: AsyncSession) -> AgentModelSettings | None:
    stmt = (
        select(AgentModelSettings)
        .where(AgentModelSettings.is_default.is_(True))
        .order_by(AgentModelSettings.created_at.asc(), AgentModelSettings.id.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_model_card(
    session: AsyncSession,
    *,
    display_name: str,
    model_name: str,
    api_key: str,
    base_url: str,
    temperature: float,
    reasoning_effort: str,
    reasoning_enabled: bool,
    is_default: bool,
    is_active: bool,
) -> AgentModelSettings:
    row = AgentModelSettings(
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
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def update_model_card(
    session: AsyncSession,
    row: AgentModelSettings,
    *,
    display_name: str,
    model_name: str,
    api_key: str,
    base_url: str,
    temperature: float,
    reasoning_effort: str,
    reasoning_enabled: bool,
    is_default: bool,
    is_active: bool,
) -> AgentModelSettings:
    row.display_name = display_name
    row.model_name = model_name
    row.api_key = api_key
    row.base_url = base_url
    row.temperature = temperature
    row.reasoning_effort = reasoning_effort
    row.reasoning_enabled = reasoning_enabled
    row.is_default = is_default
    row.is_active = is_active
    await session.commit()
    await session.refresh(row)
    return row


async def delete_model_card(session: AsyncSession, model_id: UUID) -> bool:
    row = await get_model_card(session, model_id)
    if row is None:
        return False

    await session.delete(row)
    await session.commit()
    return True


async def set_active_model_card(
    session: AsyncSession,
    model_id: UUID,
) -> AgentModelSettings | None:
    row = await get_model_card(session, model_id)
    if row is None:
        return None

    await session.execute(update(AgentModelSettings).values(is_active=False))
    row.is_active = True
    await session.commit()
    await session.refresh(row)
    return row


async def set_default_model_card(
    session: AsyncSession,
    model_id: UUID,
) -> AgentModelSettings | None:
    row = await get_model_card(session, model_id)
    if row is None:
        return None

    await session.execute(update(AgentModelSettings).values(is_default=False))
    row.is_default = True
    await session.commit()
    await session.refresh(row)
    return row


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


async def get_global_tool_settings(session: AsyncSession) -> AgentToolSettings | None:
    stmt = select(AgentToolSettings).where(AgentToolSettings.singleton_key == GLOBAL_SINGLETON_KEY)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_global_tool_settings(
    session: AsyncSession,
    *,
    tool_overrides_json: dict[str, bool],
) -> AgentToolSettings:
    row = await get_global_tool_settings(session)
    if row is None:
        row = AgentToolSettings(
            singleton_key=GLOBAL_SINGLETON_KEY,
            tool_overrides_json=tool_overrides_json,
        )
        session.add(row)
    else:
        row.tool_overrides_json = tool_overrides_json

    await session.commit()
    await session.refresh(row)
    return row


async def delete_global_tool_settings(session: AsyncSession) -> bool:
    row = await get_global_tool_settings(session)
    if row is None:
        return False

    await session.delete(row)
    await session.commit()
    return True
