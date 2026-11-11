from fastapi import APIRouter
from app.api.v1 import health, admin_catalog, auth, profile, recipients

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(admin_catalog.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(recipients.router)