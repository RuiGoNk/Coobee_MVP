import random
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_db
from app.models.catalog import CatalogItem
from app.models.recipient import Recipient
from app.models.user import User, UserProfile
from app.models.feedback import Feedback


router = APIRouter(prefix="/recommend", tags=["recommend"])


class RecommendIn(BaseModel):
    recipient_id: uuid.UUID


class RecommendItem(BaseModel):
    external_id: str
    title: str
    description: str | None
    price_min: int | None
    price_max: int | None
    image_url: str | None
    marketplace_url: str | None
    marketplaces: list[dict] | None = None
    badges: list[dict] | None = None
    why: str | None = None


class RecommendOut(BaseModel):
    items: list[RecommendItem]


def _profile_to_dict(user: User, profile: UserProfile | None) -> dict:
    return {
        "user_id": str(user.id),
        "birth_date": str(profile.birth_date) if profile and profile.birth_date else None,
        "birth_year": profile.birth_year if profile else None,
        "gender": profile.gender if profile else None,
        "occupation": profile.occupation if profile else None,
        "interests": profile.interests if profile else [],
        "style": profile.style if profile else [],
        "budget_range": profile.budget_range if profile else None,
        "city": profile.city if profile else None,
    }


def _recipient_to_dict(rec: Recipient) -> dict:
    return {
        "recipient_id": str(rec.id),
        "name": rec.name,
        "relationship": rec.relationship,
        "gender": rec.gender,
        "birth_date": str(rec.birth_date) if rec.birth_date else None,
        "age": rec.age,
        "occasion": rec.occasion,
        "relationship_level": rec.relationship_level,
        "budget_range": rec.budget_range,
        "details": rec.details or {},
    }


def _fallback_recommend(items: list[CatalogItem], recipient: dict) -> list[CatalogItem]:
    """Заглушка вместо ML: 4 по совпадению тегов/бюджета + 1 случайный 'сюрприз'."""
    interests = set(recipient.get("details", {}).get("interests", []) or [])
    budget = recipient.get("budget_range")

    def score(item: CatalogItem) -> int:
        s = 0
        tags = set(item.tags or [])
        s += len(tags & interests) * 10
        if budget == "symbolic" and (item.price_min or 0) <= 1000:
            s += 3
        elif budget == "standard" and 1000 <= (item.price_min or 0) <= 5000:
            s += 3
        elif budget == "solid" and 5000 <= (item.price_min or 0) <= 15000:
            s += 3
        elif budget == "premium" and (item.price_min or 0) >= 15000:
            s += 3
        return s

    ranked = sorted(items, key=score, reverse=True)
    return ranked[:5]


@router.post("", response_model=RecommendOut)
async def recommend(
    payload: RecommendIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rec = await db.get(Recipient, payload.recipient_id)
    if not rec or rec.user_id != user.id or rec.is_deleted:
        raise HTTPException(404, "recipient not found")

    profile_stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    profile = (await db.execute(profile_stmt)).scalar_one_or_none()

    user_dict = _profile_to_dict(user, profile)
    recipient_dict = _recipient_to_dict(rec)

    # исключаем все оценённые для этого получателя: like, dislike, have
    rated_stmt = select(Feedback.item_id).where(
        Feedback.user_id == user.id,
        Feedback.action.in_(["like", "dislike", "have"]),
        Feedback.context == "recipient",
        Feedback.recipient_id == rec.id,
    )
    rated_ids = set((await db.execute(rated_stmt)).scalars().all())

    items_stmt = select(CatalogItem).where(CatalogItem.is_available.is_(True))
    all_items = [it for it in (await db.execute(items_stmt)).scalars().all() if it.id not in rated_ids]
    # TODO: заменить на ml_service.get_recommendations(user_dict, recipient_dict)
    picked = _fallback_recommend(list(all_items), recipient_dict)

    recipient_interests = set((recipient_dict.get("details") or {}).get("interests") or [])
    out: list[RecommendItem] = []
    for it in picked[:5]:
        it_tags = set(it.tags or [])
        matched = sorted(it_tags & recipient_interests)
        why_parts = []
        if matched:
            why_parts.append(f"совпадает по интересам: {', '.join(matched)}")
        if it.price_min is not None and it.price_max is not None:
            why_parts.append(f"в бюджете {it.price_min}–{it.price_max} ₽")
        why = "; ".join(why_parts) or None

        details = it.details or {}
        out.append(RecommendItem(
            external_id=it.external_id or str(it.id),
            title=it.title,
            description=it.description,
            price_min=it.price_min,
            price_max=it.price_max,
            image_url=it.image_url,
            marketplace_url=it.marketplace_url,
            marketplaces=details.get("marketplaces"),
            badges=details.get("badges"),
            why=why,
        ))
    return RecommendOut(items=out)