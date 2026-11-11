from fastapi import APIRouter
from app.api.v1 import (
    health, admin_catalog, auth, profile, recipients, recommend, feedback,
    groups, rooms, wishlist, feed,
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
