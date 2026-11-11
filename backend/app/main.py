from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.router import api_router

app = FastAPI(title="CooBee API", version="0.1.0")
app.include_router(api_router, prefix="/api/v1")
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")