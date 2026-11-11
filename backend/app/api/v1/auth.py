import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_jwt,
    get_current_user,
    get_db,
    validate_telegram_hash,
)
from app.models.auth_session import AuthSession
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- A1: Telegram Login Widget ----------
class TelegramAuthIn(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


@router.post("/telegram")
async def auth_telegram(payload: TelegramAuthIn, db: AsyncSession = Depends(get_db)):
    data = payload.model_dump()
    if not validate_telegram_hash(data, settings.TELEGRAM_BOT_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid telegram hash")

    tg_id = payload.id
    stmt = select(User).where(User.telegram_id == tg_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        user = User(telegram_id=tg_id, username=payload.username)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_jwt(str(user.id))
    return {"access_token": token, "token_type": "bearer", "user_id": str(user.id)}


# ---------- A2: deep link через бота ----------
class SessionOut(BaseModel):
    session_id: str
    deep_link: str
    expires_at: datetime


@router.post("/session", response_model=SessionOut)
async def create_session(db: AsyncSession = Depends(get_db)):
    sess = AuthSession(
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    deep_link = f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start=auth_{sess.id}"
    return SessionOut(session_id=str(sess.id), deep_link=deep_link, expires_at=sess.expires_at)


class SessionStatusOut(BaseModel):
    status: str
    access_token: str | None = None
    token_type: str | None = None
    user_id: str | None = None


@router.get("/session/{session_id}", response_model=SessionStatusOut)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    sess = await db.get(AuthSession, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="session not found")
    if sess.expires_at < datetime.now(timezone.utc):
        if sess.status != "expired":
            sess.status = "expired"
            await db.commit()
        return SessionStatusOut(status="expired")
    if sess.status == "confirmed" and sess.user_id:
        token = create_jwt(str(sess.user_id))
        return SessionStatusOut(status="confirmed", access_token=token, token_type="bearer", user_id=str(sess.user_id))
    return SessionStatusOut(status=sess.status)


# ---------- Текущий пользователь ----------
class MeOut(BaseModel):
    id: str
    telegram_id: int
    username: str | None


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(get_current_user)):
    return MeOut(id=str(user.id), telegram_id=user.telegram_id, username=user.username)