from fastapi import APIRouter

from server.features.agent.api.router import router as agent_router
from server.features.attachments.api.router import router as attachments_router
from server.features.chat.api import router as conversations_router
from server.features.settings.api import router as settings_router
from server.features.tables.api import router as tables_router

api_router = APIRouter()
api_router.include_router(agent_router)
api_router.include_router(attachments_router)
api_router.include_router(conversations_router)
api_router.include_router(settings_router)
api_router.include_router(tables_router)
