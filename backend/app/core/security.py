import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User


# ---------- Admin ----------
async def require_admin(x_admin_token: str = Header(default="")) -> None:
    if not x_admin_token or x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")


# ---------- Telegram hash validation (A1) ----------
def validate_telegram_hash(data: dict[str, Any], bot_token: str, ttl_seconds: int = 86400) -> bool:
    """
    Проверяет hash от Telegram Login Widget.
    data: поля от виджета (id, first_name, username, auth_date, hash, ...)
    """
    received_hash = data.get("hash")
    if not received_hash:
        return False

    auth_date = data.get("auth_date")
    if auth_date is None:
        return False
    try:
        auth_ts = int(auth_date)
    except (TypeError, ValueError):
        return False
    if time.time() - auth_ts > ttl_seconds:
        return False  # просрочен

    pairs = []
    for k, v in data.items():
        if k == "hash":
            continue
        if v is None:
            continue
        pairs.append(f"{k}={v}")
    pairs.sort()
    data_check_string = "\n".join(pairs)

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, received_hash)


# ---------- JWT ----------
def create_jwt(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.JWT_EXPIRE_DAYS)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALG)


def decode_jwt(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALG])
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"invalid token: {e}")


# ---------- Dependencies ----------
async def get_db():
    async with SessionLocal() as s:
        yield s


async def get_current_user(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token payload")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user