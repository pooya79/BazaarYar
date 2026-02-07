from fastapi import APIRouter

from .agents import router as agents_router
from .conversations import router as conversations_router
from .tables import router as tables_router

api_router = APIRouter()
api_router.include_router(agents_router)
api_router.include_router(conversations_router)
api_router.include_router(tables_router)
