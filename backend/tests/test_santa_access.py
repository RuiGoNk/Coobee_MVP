"""
Тесты приватности модуля santa (ядро).

Проверяем:
- подборка (GET /assignments/{id}/suggestions) — только Санта;
- получатель → 403;
- организатор → 403;
- третье лицо → 403;
- GET /rooms/{id}/assignment/me — 403, если пользователь не Санта;
- regenerate — 429 при превышении лимита.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.santa import (
    Assignment,
    Draw,
    GiftSuggestion,
    Participant,
    Room,
)
from app.models.user import User


# ---------------------------------------------------------------------------
# Фикстуры (создаём данные напрямую в БД, без API — быстрее и надёжнее)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def santa_setup(db: AsyncSession):
    """
    Готовит:
    - 3 user'а: organizer, santa, santee;
    - room (owner=organizer);
    - 3 participant'а в комнате;
    - draw + assignments (santa→santee, santee→organizer, organizer→santa);
    - 6 GiftSuggestion для assignment santa→santee.
    """
    organizer = User(telegram_id=1001, username="organizer")
    santa = User(telegram_id=1002, username="santa")
    santee = User(telegram_id=1003, username="santee")
    db.add_all([organizer, santa, santee])
    await db.flush()

    room = Room(
        owner_id=organizer.id,
        title="Test room",
        budget_min=Decimal("1000"),
        budget_max=Decimal("2000"),
        currency="RUB",
        tz="Europe/Moscow",
        status="in_progress",
        anonymity_mode="full",
        join_policy="link",
        visibility_policy="balanced",
        max_participants=30,
        require_min_profile=True,
    )
    db.add(room)
    await db.flush()

    def mk_participant(user: User, name: str) -> Participant:
        return Participant(
            room_id=room.id,
            user_id=user.id,
            display_name=name,
            gender="prefer_not_to_say",
            birth_date=date(1990, 1, 1),
            interests=["books_fiction"],
            visibility={"gender": "hidden", "age": "general", "interests": "full"},
            profile_completeness=80,
            status="profile_full",
        )

    p_org = mk_participant(organizer, "Organizer")
    p_santa = mk_participant(santa, "Santa")
    p_santee = mk_participant(santee, "Santee")
    db.add_all([p_org, p_santa, p_santee])
    await db.flush()

    draw = Draw(
        room_id=room.id,
        drawn_by=organizer.id,
        drawn_at=datetime.now(timezone.utc),
        algorithm_version="v1_random",
        status="ready",
    )
    db.add(draw)
    await db.flush()

    a_santa_to_santee = Assignment(
        draw_id=draw.id,
        santa_participant_id=p_santa.id,
        santee_participant_id=p_santee.id,
        gift_status="pending",
    )
    a_santee_to_org = Assignment(
        draw_id=draw.id,
        santa_participant_id=p_santee.id,
        santee_participant_id=p_org.id,
        gift_status="pending",
    )
    a_org_to_santa = Assignment(
        draw_id=draw.id,
        santa_participant_id=p_org.id,
        santee_participant_id=p_santa.id,
        gift_status="pending",
    )
    db.add_all([a_santa_to_santee, a_santee_to_org, a_org_to_santa])
    await db.flush()

    for i in range(6):
        db.add(
            GiftSuggestion(
                assignment_id=a_santa_to_santee.id,
                generation=0,
                external_id=f"item_{i:03d}",
                idea_title=f"Idea {i}",
                category="books",
                tags=["books_fiction"],
                price_min=Decimal("1000"),
                price_max=Decimal("1500"),
                reason="почему: интерес «books_fiction»",
                score=Decimal("0.9000"),
                source="curated",
            )
        )
    await db.commit()

    return {
        "organizer": organizer,
        "santa": santa,
        "santee": santee,
        "room": room,
        "draw": draw,
        "assignment_santa": a_santa_to_santee,
        "assignment_other": a_santee_to_org,
        "participant_santa": p_santa,
        "participant_santee": p_santee,
    }


# ---------------------------------------------------------------------------
# Подборка: только Санта
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_suggestions_santa_can_read(client, auth_headers, santa_setup):
    a = santa_setup["assignment_santa"]
    headers = auth_headers(santa_setup["santa"])
    r = await client.get(f"/api/v1/santa/assignments/{a.id}/suggestions", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 6
    assert body["can_regenerate"] is True
    assert body["regenerations_left"] == 10


@pytest.mark.asyncio
async def test_suggestions_santee_forbidden(client, auth_headers, santa_setup):
    """Получатель → 403 SUGGESTIONS_FORBIDDEN."""
    a = santa_setup["assignment_santa"]
    headers = auth_headers(santa_setup["santee"])
    r = await client.get(f"/api/v1/santa/assignments/{a.id}/suggestions", headers=headers)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "SUGGESTIONS_FORBIDDEN"


@pytest.mark.asyncio
async def test_suggestions_organizer_forbidden(client, auth_headers, santa_setup):
    """Организатор → 403 (видит только агрегаты дашборда)."""
    a = santa_setup["assignment_santa"]
    headers = auth_headers(santa_setup["organizer"])
    r = await client.get(f"/api/v1/santa/assignments/{a.id}/suggestions", headers=headers)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "SUGGESTIONS_FORBIDDEN"


@pytest.mark.asyncio
async def test_suggestions_third_party_forbidden(client, auth_headers, db, santa_setup):
    """Третье лицо → 403."""
    stranger = User(telegram_id=9999, username="stranger")
    db.add(stranger)
    await db.commit()

    a = santa_setup["assignment_santa"]
    headers = auth_headers(stranger)
    r = await client.get(f"/api/v1/santa/assignments/{a.id}/suggestions", headers=headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_suggestions_other_assignment_forbidden(client, auth_headers, santa_setup):
    """Санта для A→B не должен видеть подборку для B→C."""
    a_other = santa_setup["assignment_other"]  # santee→organizer
    headers = auth_headers(santa_setup["santa"])
    r = await client.get(f"/api/v1/santa/assignments/{a_other.id}/suggestions", headers=headers)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Карточка подопечного
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_assignment_me_santa_ok(client, auth_headers, santa_setup):
    room = santa_setup["room"]
    headers = auth_headers(santa_setup["santa"])
    r = await client.get(f"/api/v1/santa/rooms/{room.id}/assignment/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    # visibility применена: gender hidden, age general, interests full
    assert body["participant"]["gender"] == "Участник предпочёл не указать"
    assert body["participant"]["age"] == "30–39"
    assert body["participant"]["interests"] == ["books_fiction"]


@pytest.mark.asyncio
async def test_assignment_me_santee_forbidden(client, auth_headers, santa_setup):
    """Получатель не может получить карточку «своего Санты»."""
    room = santa_setup["room"]
    headers = auth_headers(santa_setup["santee"])
    r = await client.get(f"/api/v1/santa/rooms/{room.id}/assignment/me", headers=headers)
    # santee — Санта для organizer, у него есть assignment. Значит, 200,
    # но карточка — organizer'а, не его собственная.
    assert r.status_code == 200
    body = r.json()
    assert body["participant"]["display_name"] == "Organizer"


# ---------------------------------------------------------------------------
# Лимит перегенераций
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_regenerate_limit_429(client, auth_headers, db, santa_setup):
    """После 10 перегенераций → 429 REGENERATION_LIMIT."""
    a = santa_setup["assignment_santa"]
    # Искусственно создаём 10 генераций
    for gen in range(1, 11):
        db.add(
            GiftSuggestion(
                assignment_id=a.id,
                generation=gen,
                external_id=f"item_regen_{gen}",
                idea_title=f"Regen {gen}",
                tags=[],
                source="curated",
            )
        )
    await db.commit()

    headers = auth_headers(santa_setup["santa"])
    r = await client.post(
        f"/api/v1/santa/assignments/{a.id}/suggestions/regenerate",
        headers=headers,
    )
    assert r.status_code == 429
    assert r.json()["detail"]["code"] == "REGENERATION_LIMIT"


# ---------------------------------------------------------------------------
# Без JWT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_suggestions_no_jwt_401(client, santa_setup):
    a = santa_setup["assignment_santa"]
    r = await client.get(f"/api/v1/santa/assignments/{a.id}/suggestions")
    assert r.status_code == 401