"""
Общие фикстуры для тестов.

- db: AsyncSession из SessionLocal.
- client: AsyncClient с ASGITransport (без реального сервера).
- auth_headers(user): JWT-заголовок для пользователя.
- db_cleanup: после каждого теста чистим santa_* и тестовых users
  (telegram_id >= 1000 — тестовый диапазон, не задеваем реальных).
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.security import create_jwt
from app.db.session import SessionLocal
from app.main import app
from app.models.santa import (
    Assignment,
    Draw,
    Exclusion,
    GiftSuggestion,
    Invite,
    Message,
    Notification,
    Participant,
    Room,
)
from app.models.user import User


# ---------------------------------------------------------------------------
# Event loop (один на сессию pytest)
# ---------------------------------------------------------------------------
# Причина: asyncpg-пул привязан к loop'у, в котором создан engine.
# pytest-asyncio 0.24 не поддерживает asyncio_default_fixture_loop_scope,
# поэтому задаём loop явно. DeprecationWarning игнорируем — до перехода
# на pytest-asyncio 0.25+ заменить на "scope" в asyncio mark.

import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# БД
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db():
    async with SessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# HTTP-клиент
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_headers():
    def _make(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_jwt(str(user.id))}"}
    return _make


# ---------------------------------------------------------------------------
# Чистка после теста
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def db_cleanup():
    """
    До и после теста — чистим santa_* и тестовых users.
    autouse=True, чтобы не забывать в каждом тесте.
    """
    async def _cleanup():
        async with SessionLocal() as session:
            # Порядок важен из-за FK
            await session.execute(delete(GiftSuggestion))
            await session.execute(delete(Message))
            await session.execute(delete(Notification))
            await session.execute(delete(Assignment))
            await session.execute(delete(Exclusion))
            await session.execute(delete(Invite))
            await session.execute(delete(Participant))
            await session.execute(delete(Draw))
            await session.execute(delete(Room))
            # Тестовые users — по telegram_id >= 1000
            await session.execute(delete(User).where(User.telegram_id >= 1000))
            await session.commit()

    await _cleanup()
    yield
    await _cleanup()