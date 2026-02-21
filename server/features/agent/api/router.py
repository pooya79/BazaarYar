from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_db_session
from server.features.agent.api.message_builders import build_messages
from server.features.agent.api.schemas import AgentRequest, AgentResponse
from server.features.agent.api import streaming
from server.features.agent.schemas import stream_event_schema
from server.features.agent.sandbox.event_bus import AgentRequestContext, bind_request_context
from server.features.agent.sandbox.session_executor import reset_conversation_sandbox
from server.features.agent.service import extract_trace
from server.features.settings.service import (
    resolve_effective_company_profile,
    resolve_effective_model_settings,
    resolve_effective_tool_settings,
)
from server.features.shared.ids import parse_uuid

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
    model_settings = await resolve_effective_model_settings(session)
    company_profile = await resolve_effective_company_profile(session)
    tool_settings = await resolve_effective_tool_settings(session)
    agent = streaming.get_agent(model_settings, company_profile, tool_settings)
    request_context = AgentRequestContext(
        latest_user_message=(payload.message or "").strip(),
        latest_user_attachment_ids=tuple(
            item.strip() for item in (payload.attachment_ids or []) if item.strip()
        ),
        conversation_id=payload.conversation_id,
    )
    with bind_request_context(request_context):
        result = await agent.ainvoke({"messages": messages})
    trace = extract_trace(result["messages"], model_name=model_settings.model_name)
    return AgentResponse(**trace)


@router.post("/stream")
async def stream_agent(
    payload: AgentRequest,
    session: AsyncSession = Depends(get_db_session),
):
    return await streaming.stream_agent_response(payload, session=session)


@router.post("/conversations/{conversation_id}/sandbox/reset")
async def reset_conversation_sandbox_session(
    conversation_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    conversation_uuid = parse_uuid(conversation_id, field_name="conversation_id")
    reset = await reset_conversation_sandbox(
        session,
        conversation_id=str(conversation_uuid),
    )
    return {"reset": reset}
