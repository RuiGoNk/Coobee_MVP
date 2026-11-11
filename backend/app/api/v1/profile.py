from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_db
from app.models.user import User, UserProfile

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileIn(BaseModel):
    birth_date: date | None = None
    birth_year: int | None = None
    gender: str | None = None
    occupation: str | None = None
    interests: list[str] | None = None
    style: list[str] | None = None
    budget_range: str | None = None
    city: str | None = None

    @model_validator(mode="after")
    def check_age(self):
        if self.birth_date is None and self.birth_year is None:
            raise ValueError("нужен birth_date или birth_year")
        return self


class ProfileOut(ProfileIn):
    model_config = {"from_attributes": True}


@router.get("/me", response_model=ProfileOut | None)
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    return (await db.execute(stmt)).scalar_one_or_none()


@router.put("/me", response_model=ProfileOut)
async def upsert_my_profile(
    payload: ProfileIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user.id, **payload.model_dump())
        db.add(profile)
    else:
        for k, v in payload.model_dump().items():
            setattr(profile, k, v)
    await db.commit()
    await db.refresh(profile)
    return profile