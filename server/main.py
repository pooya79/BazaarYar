from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agents.api import router as agent_router
from .core.config import get_settings
from .db.session import async_engine

settings = get_settings()

app = FastAPI(title="BazaarYar API", docs_url="/api/docs")
app.include_router(agent_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db() -> None:
    await async_engine.dispose()


@app.get("/")
async def read_root() -> dict:
    return {"status": "ok", "service": "bazaaryar"}


@app.get("/health")
async def health_check() -> dict:
    return {"healthy": True}
