import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_db
from app.models.catalog import CatalogItem
from app.models.feedback import Feedback
from app.models.recipient import Recipient
from app.models.user import User

router = APIRouter(prefix="/feedback", tags=["feedback"])

ALLOWED_ACTIONS = {"like", "dislike", "have"}
ALLOWED_CONTEXTS = {"recipient", "self_wishlist"}


class FeedbackIn(BaseModel):
    external_id: str
    action: str
    context: str = "recipient"
    recipient_id: uuid.UUID | None = None

    @field_validator("action")
    @classmethod
    def check_action(cls, v: str) -> str:
        if v not in ALLOWED_ACTIONS:
            raise ValueError("action must be like|dislike|have")
        return v

    @field_validator("context")
    @classmethod
    def check_context(cls, v: str) -> str:
        if v not in ALLOWED_CONTEXTS:
            raise ValueError("context must be recipient|self_wishlist")
        return v


class FeedbackOut(BaseModel):
    id: uuid.UUID
    external_id: str
    action: str
    context: str
    recipient_id: uuid.UUID | None


async def _get_item(external_id: str, db: AsyncSession) -> CatalogItem:
    stmt = select(CatalogItem).where(CatalogItem.external_id == external_id)
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "catalog item not found")
    return item


@router.post("", response_model=FeedbackOut)
async def upsert_feedback(
    payload: FeedbackIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_item(payload.external_id, db)

    if payload.context == "recipient":
        if not payload.recipient_id:
            raise HTTPException(400, "recipient_id required for context=recipient")
        rec = await db.get(Recipient, payload.recipient_id)
        if not rec or rec.user_id != user.id or rec.is_deleted:
            raise HTTPException(404, "recipient not found")
        stmt = select(Feedback).where(
            Feedback.user_id == user.id,
            Feedback.item_id == item.id,
            Feedback.context == "recipient",
            Feedback.recipient_id == payload.recipient_id,
        )
    else:  # self_wishlist
        stmt = select(Feedback).where(
            Feedback.user_id == user.id,
            Feedback.item_id == item.id,
            Feedback.context == "self_wishlist",
        )

    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.action = payload.action
        fb = existing
    else:
        fb = Feedback(
            user_id=user.id,
            item_id=item.id,
            recipient_id=payload.recipient_id if payload.context == "recipient" else None,
            action=payload.action,
            context=payload.context,
        )
        db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return FeedbackOut(
        id=fb.id,
        external_id=payload.external_id,
        action=fb.action,
        context=fb.context,
        recipient_id=fb.recipient_id,
    )


@router.delete("/{external_id}", status_code=204)
async def remove_feedback(
    external_id: str,
    context: str = "recipient",
    recipient_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_item(external_id, db)

    if context == "recipient":
        if not recipient_id:
            raise HTTPException(400, "recipient_id required for context=recipient")
        stmt = select(Feedback).where(
            Feedback.user_id == user.id,
            Feedback.item_id == item.id,
            Feedback.context == "recipient",
            Feedback.recipient_id == recipient_id,
        )
    else:
        stmt = select(Feedback).where(
            Feedback.user_id == user.id,
            Feedback.item_id == item.id,
            Feedback.context == "self_wishlist",
        )

    fb = (await db.execute(stmt)).scalar_one_or_none()
    if not fb:
        raise HTTPException(404, "feedback not found")
    await db.delete(fb)
    await db.commit()
    return None