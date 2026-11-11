from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_db
from app.models.catalog import CatalogItem
from app.models.feedback import Feedback
from app.models.user import User

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


def _item_out(it: CatalogItem) -> dict:
    return {
        "external_id": it.external_id,
        "title": it.title,
        "description": it.description,
        "price_min": it.price_min,
        "price_max": it.price_max,
        "image_url": it.image_url,
        "marketplace_url": it.marketplace_url,
        "tags": it.tags,
    }


@router.get("", response_model=list[dict])
async def get_wishlist(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CatalogItem)
        .join(Feedback, Feedback.item_id == CatalogItem.id)
        .where(
            Feedback.user_id == user.id,
            Feedback.action == "like",
            Feedback.context == "self_wishlist",
            CatalogItem.is_available.is_(True),
        )
        .order_by(Feedback.created_at.desc())
    )
    items = (await db.execute(stmt)).scalars().all()
    return [_item_out(it) for it in items]


@router.post("/{external_id}", response_model=dict)
async def add_to_wishlist(
    external_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item_stmt = select(CatalogItem).where(CatalogItem.external_id == external_id)
    item = (await db.execute(item_stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "catalog item not found")

    stmt = select(Feedback).where(
        Feedback.user_id == user.id,
        Feedback.item_id == item.id,
        Feedback.context == "self_wishlist",
    )
    fb = (await db.execute(stmt)).scalar_one_or_none()
    if fb:
        fb.action = "like"
    else:
        fb = Feedback(
            user_id=user.id,
            item_id=item.id,
            recipient_id=None,
            action="like",
            context="self_wishlist",
        )
        db.add(fb)
    await db.commit()
    return _item_out(item)


@router.delete("/{external_id}", status_code=204)
async def remove_from_wishlist(
    external_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item_stmt = select(CatalogItem).where(CatalogItem.external_id == external_id)
    item = (await db.execute(item_stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "catalog item not found")

    stmt = select(Feedback).where(
        Feedback.user_id == user.id,
        Feedback.item_id == item.id,
        Feedback.context == "self_wishlist",
    )
    fb = (await db.execute(stmt)).scalar_one_or_none()
    if not fb:
        raise HTTPException(404, "not in wishlist")
    await db.delete(fb)
    await db.commit()
    return None