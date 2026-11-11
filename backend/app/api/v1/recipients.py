import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_db
from app.models.recipient import Recipient
from app.models.user import User

router = APIRouter(prefix="/recipients", tags=["recipients"])


class RecipientIn(BaseModel):
    name: str
    relationship: str
    gender: str = "unisex"
    birth_date: date | None = None
    age: int | None = None
    occasion: str | None = None
    relationship_level: str | None = None
    budget_range: str | None = None
    details: dict | None = None

    @model_validator(mode="after")
    def check_age(self):
        if self.birth_date is None and self.age is None:
            raise ValueError("нужен birth_date или age")
        return self


class RecipientOut(RecipientIn):
    id: uuid.UUID
    is_deleted: bool
    model_config = {"from_attributes": True}


@router.get("", response_model=list[RecipientOut])
async def list_recipients(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Recipient).where(
        Recipient.user_id == user.id,
        Recipient.is_deleted.is_(False),
    ).order_by(Recipient.created_at)
    return (await db.execute(stmt)).scalars().all()


@router.post("", response_model=RecipientOut, status_code=201)
async def create_recipient(
    payload: RecipientIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump()
    if data.get("age") is not None:
        data["age_updated_at"] = datetime.now(timezone.utc)
    rec = Recipient(user_id=user.id, **data)
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec


@router.put("/{recipient_id}", response_model=RecipientOut)
async def update_recipient(
    recipient_id: uuid.UUID,
    payload: RecipientIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rec = await db.get(Recipient, recipient_id)
    if not rec or rec.user_id != user.id or rec.is_deleted:
        raise HTTPException(404, "recipient not found")
    data = payload.model_dump()
    if data.get("age") is not None:
        data["age_updated_at"] = datetime.now(timezone.utc)
    for k, v in data.items():
        setattr(rec, k, v)
    await db.commit()
    await db.refresh(rec)
    return rec


@router.delete("/{recipient_id}", status_code=204)
async def delete_recipient(
    recipient_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rec = await db.get(Recipient, recipient_id)
    if not rec or rec.user_id != user.id or rec.is_deleted:
        raise HTTPException(404, "recipient not found")
    rec.is_deleted = True
    await db.commit()
    return None