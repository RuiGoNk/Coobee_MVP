import random

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_db
from app.models.catalog import CatalogItem
from app.models.feedback import Feedback
from app.models.user import User, UserProfile

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=list[dict])
async def get_feed(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # исключаем: вишлист-лайки + «у меня уже есть»
    excluded_stmt = select(Feedback.item_id).where(
        Feedback.user_id == user.id,
        Feedback.context == "self_wishlist",
        Feedback.action.in_(["like", "have"]),
    )
    excluded_ids = set((await db.execute(excluded_stmt)).scalars().all())

    prof_stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    profile = (await db.execute(prof_stmt)).scalar_one_or_none()
    interests = set(profile.interests or []) if profile else set()

    items_stmt = select(CatalogItem).where(CatalogItem.is_available.is_(True))
    all_items = [it for it in (await db.execute(items_stmt)).scalars().all() if it.id not in excluded_ids]

    def score(it: CatalogItem) -> int:
        return len(set(it.tags or []) & interests)

    ranked = sorted(all_items, key=score, reverse=True)[:30]
    random.shuffle(ranked)
    return [
        {
            "external_id": it.external_id,
            "title": it.title,
            "description": it.description,
            "price_min": it.price_min,
            "price_max": it.price_max,
            "image_url": it.image_url,
            "marketplace_url": it.marketplace_url,
            "tags": it.tags,
        }
        for it in ranked
    ]