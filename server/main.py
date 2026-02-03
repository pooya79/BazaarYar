from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agents.api import router as agent_router
from .core.config import get_settings

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

@app.get("/")
def read_root() -> dict:
    return {"status": "ok", "service": "bazaaryar"}


@app.get("/health")
def health_check() -> dict:
    return {"healthy": True}
