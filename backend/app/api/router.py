from fastapi import APIRouter
from app.api.v1 import (
    admin_catalog,
    auth,
    feed,
    feedback,
    groups,
    health,
    profile,
    recipients,
    recommend,
    rooms,
    santa_draw,
    santa_misc,
    santa_rooms,
    wishlist,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(admin_catalog.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(recipients.router)
api_router.include_router(recommend.router)
api_router.include_router(feedback.router)
api_router.include_router(wishlist.router)
api_router.include_router(feed.router)
api_router.include_router(groups.router)
api_router.include_router(rooms.router)

# --- Santa module ---
api_router.include_router(santa_rooms.router, prefix="/santa")
api_router.include_router(santa_draw.router, prefix="/santa")
api_router.include_router(santa_misc.router, prefix="/santa")
