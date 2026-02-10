import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .core.config import get_settings
from .db.session import AsyncSessionLocal, async_engine
from .features.agent.observability import configure_agent_observability
from .features.agent.sandbox.session_executor import cleanup_stale_sandbox_sessions

settings = get_settings()


async def _sandbox_sweeper_loop() -> None:
    while True:
        try:
            async with AsyncSessionLocal() as session:
                await cleanup_stale_sandbox_sessions(session)
        except Exception:
            # Cleanup is best-effort and should not crash app lifespan loop.
            pass
        interval = max(1, settings.sandbox_session_sweep_interval_seconds)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_agent_observability()
    sweeper_task: asyncio.Task[None] | None = None
    if settings.sandbox_tool_enabled and settings.sandbox_persist_sessions:
        sweeper_task = asyncio.create_task(_sandbox_sweeper_loop())
    try:
        yield
    finally:
        if sweeper_task is not None:
            sweeper_task.cancel()
            with suppress(asyncio.CancelledError):
                await sweeper_task
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
