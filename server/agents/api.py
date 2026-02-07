"""Compatibility layer for API routers moved to ``server.api``."""

from server.api.agents.router import router
from server.api.conversations.router import router as conversations_router

__all__ = ["router", "conversations_router"]
