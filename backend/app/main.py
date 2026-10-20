from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.research import router as research_router
import logging

from app.routes.documents import router as documents_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # keep per-request noise out

from app.config import get_settings

settings = get_settings()

app = FastAPI(title="DeepCites API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(research_router)
app.include_router(documents_router)


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}