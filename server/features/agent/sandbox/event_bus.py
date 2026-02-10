from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable


@dataclass(frozen=True)
class AgentRequestContext:
    latest_user_message: str
    latest_user_attachment_ids: tuple[str, ...]
    conversation_id: str | None = None


@dataclass(frozen=True)
class SandboxStatusPayload:
    run_id: str
    stage: str
    message: str
    timestamp: datetime


EventSink = Callable[[SandboxStatusPayload], Awaitable[None]]

_event_sink_var: ContextVar[EventSink | None] = ContextVar("agent_event_sink", default=None)
_request_context_var: ContextVar[AgentRequestContext | None] = ContextVar(
    "agent_request_context",
    default=None,
)


@contextmanager
def bind_event_sink(sink: EventSink):
    token = _event_sink_var.set(sink)
    try:
        yield
    finally:
        _event_sink_var.reset(token)


@contextmanager
def bind_request_context(context: AgentRequestContext):
    token = _request_context_var.set(context)
    try:
        yield
    finally:
        _request_context_var.reset(token)


def get_request_context() -> AgentRequestContext | None:
    return _request_context_var.get()


async def emit_sandbox_status(
    *,
    run_id: str,
    stage: str,
    message: str,
) -> None:
    sink = _event_sink_var.get()
    if sink is None:
        return

    await sink(
        SandboxStatusPayload(
            run_id=run_id,
            stage=stage,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )
    )
