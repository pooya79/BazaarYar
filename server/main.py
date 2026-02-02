from fastapi import FastAPI

app = FastAPI(title="BazaarYar API", docs_url="/api/docs")

@app.get("/")
def read_root() -> dict:
    return {"status": "ok", "service": "bazaaryar"}


@app.get("/health")
def health_check() -> dict:
    return {"healthy": True}
