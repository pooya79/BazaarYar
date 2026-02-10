from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .core.config import get_settings
from .db.session import async_engine
from .features.agent.observability import configure_agent_observability

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_agent_observability()
    try:
        yield
    finally:
        await async_engine.dispose()


app = FastAPI(title="BazaarYar API", docs_url="/api/docs", lifespan=lifespan)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root() -> dict:
    return {"status": "ok", "service": "bazaaryar"}


@app.get("/health")
async def health_check() -> dict:
    return {"healthy": True}
