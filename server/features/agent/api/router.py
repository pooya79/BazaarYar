from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_db_session
from server.features.agent.api.message_builders import build_messages
from server.features.agent.api.schemas import AgentRequest, AgentResponse
from server.features.agent.api import streaming
from server.features.agent.schemas import stream_event_schema
from server.features.agent.service import extract_trace

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/stream/schema")
async def stream_schema() -> dict[str, Any]:
    return stream_event_schema()


@router.post("", response_model=AgentResponse)
async def run_agent(
    payload: AgentRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    messages = await build_messages(payload, session)
    if not messages:
        raise HTTPException(status_code=400, detail="Provide message or history.")
    agent = streaming.get_agent()
    result = await agent.ainvoke({"messages": messages})
    trace = extract_trace(result["messages"])
    return AgentResponse(**trace)


@router.post("/stream")
async def stream_agent(
    payload: AgentRequest,
    session: AsyncSession = Depends(get_db_session),
):
    return await streaming.stream_agent_response(payload, session=session)
