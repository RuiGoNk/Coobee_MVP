"""
Роутер модуля santa: жеребьёвка, assignment, подборка.

Пути (под /api/v1/santa):
- POST   /rooms/{id}/draw                          — жеребьёвка (организатор)
- GET    /rooms/{id}/draw                          — последний draw (организатор)
- GET    /rooms/{id}/assignment/me                 — карточка подопечного (Санта)
- GET    /assignments/{id}/suggestions             — подборка 6 идей (Санта)
- POST   /assignments/{id}/suggestions/regenerate  — +4 идеи (Санта)
- PATCH  /assignments/{id}/gift-status             — статус подарка (Санта)

Критично: подборка и карточка подопечного — ТОЛЬКО Санта (get_current_santa).
Получатель, организатор, третьи лица → 403.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_db
from app.models.santa import (
    Assignment,
    Draw,
    GiftSuggestion,
    Participant,
    Room,
)
from app.models.user import User
from app.schemas.santa import (
    DrawCreate,
    DrawOut,
    GiftStatusUpdate,
    RegenerateOut,
    SanteeCardOut,
    SuggestionItemOut,
    SuggestionsOut,
)
from app.services.santa import draw as draw_svc
from app.services.santa import suggestions as sug_svc
from app.services.santa.access import (
    ensure_draw_possible,
    get_assignment_or_404,
    get_current_organizer,
    get_current_santa,
    get_latest_draw,
)
from app.services.santa.visibility import apply_visibility


router = APIRouter(tags=["santa: draw & suggestions"])


# ---------------------------------------------------------------------------
# Жеребьёвка
# ---------------------------------------------------------------------------

@router.post("/rooms/{room_id}/draw", response_model=DrawOut)
async def start_draw(
    payload: DrawCreate,
    db: AsyncSession = Depends(get_db),
    room: Room = Depends(get_current_organizer),
    user: User = Depends(get_current_user),
) -> dict:
    await ensure_draw_possible(db, room)

    d = await draw_svc.run_draw(
        db, room, drawn_by=user.id, mode=payload.mode,
    )
    await db.commit()
    await db.refresh(d)

    # Генерация подборок — в Celery. Если брокер недоступен (dev),
    # fallback на синхронную генерацию, чтобы MVP работал без воркера.
    try:
        from app.tasks import santa_generate_suggestions

        santa_generate_suggestions.delay(str(d.id))
    except Exception:  # noqa: BLE001
        await _generate_suggestions_for_draw(db, room, d)

    return {
        "id": d.id,
        "room_id": d.room_id,
        "drawn_at": d.drawn_at,
        "drawn_by": d.drawn_by,
        "algorithm_version": d.algorithm_version,
        "status": d.status,
    }


@router.get("/rooms/{room_id}/draw", response_model=DrawOut)
async def get_draw(
    db: AsyncSession = Depends(get_db),
    room: Room = Depends(get_current_organizer),
) -> dict:
    d = await get_latest_draw(db, room.id)
    if d is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DRAW_NOT_FOUND", "message": "Жеребьёвка не проводилась"},
        )
    return {
        "id": d.id,
        "room_id": d.room_id,
        "drawn_at": d.drawn_at,
        "drawn_by": d.drawn_by,
        "algorithm_version": d.algorithm_version,
        "status": d.status,
    }


async def _generate_suggestions_for_draw(
    db: AsyncSession, room: Room, d
) -> None:
    """
    Fallback: синхронная генерация подборок, если Celery недоступен.
    Основной путь — Celery-таск santa_generate_suggestions (Шаг 6).
    """
    from app.services.santa.generation import generate_for_draw

    await generate_for_draw(db, d.id, send_notifications=False)
    await db.commit()


# ---------------------------------------------------------------------------
# Карточка подопечного (Санта)
# ---------------------------------------------------------------------------

@router.get("/rooms/{room_id}/assignment/me", response_model=SanteeCardOut)
async def get_my_assignment(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    # Находим participant текущего пользователя
    p_stmt = select(Participant).where(
        Participant.room_id == room_id,
        Participant.user_id == user.id,
        Participant.is_deleted.is_(False),
    )
    participant = (await db.execute(p_stmt)).scalar_one_or_none()
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "NOT_IN_ROOM", "message": "Вы не участник комнаты"},
        )

    # Его assignment как Санты
    a_stmt = (
        select(Assignment)
        .where(Assignment.santa_participant_id == participant.id)
        .order_by(Assignment.id.desc())
        .limit(1)
    )
    assignment = (await db.execute(a_stmt)).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DRAW_NOT_DONE",
                "message": "Жеребьёвка ещё не проведена или вы не Санта",
            },
        )

    room = await db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail={"code": "ROOM_NOT_FOUND"})

    santee = await db.get(Participant, assignment.santee_participant_id)
    if santee is None or santee.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SANTEE_DELETED", "message": "Подопечный удалился"},
        )

    # Отмечаем viewed_at (для FR-4.9)
    if assignment.viewed_at is None:
        assignment.viewed_at = datetime.now(timezone.utc)
        await db.commit()

    fields = apply_visibility(santee)
    hints: list[str] = []
    if santee.status == "profile_min":
        hints.append("Получатель заполнил минимум — идеи общие")
    hidden = [f for f, m in (santee.visibility or {}).items() if m == "hidden"]
    if hidden:
        hints.append("Получатель предпочёл скрыть детали — идеи универсальные")

    return {
        "assignment_id": assignment.id,
        "participant": fields,
        "budget_min": room.budget_min,
        "budget_max": room.budget_max,
        "currency": room.currency,
        "gift_status": assignment.gift_status,
        "viewed_at": assignment.viewed_at,
        "pickup_point": santee.pickup_point,  # только Санте после draw
        "hints": hints,
    }


# ---------------------------------------------------------------------------
# Подборка (Санта)
# ---------------------------------------------------------------------------

@router.get(
    "/assignments/{assignment_id}/suggestions",
    response_model=SuggestionsOut,
)
async def get_suggestions(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    assignment: Assignment = Depends(get_current_santa),
) -> dict:
    room = await _room_for_assignment(db, assignment)
    used = await sug_svc.regenerations_used(db, assignment.id)

    stmt = (
        select(GiftSuggestion)
        .where(
            GiftSuggestion.assignment_id == assignment.id,
            GiftSuggestion.generation == 0,
        )
        .order_by(GiftSuggestion.score.desc().nulls_last())
    )
    items = list((await db.execute(stmt)).scalars().all())

    return {
        "assignment_id": assignment.id,
        "generation": 0,
        "items": [_to_item(i) for i in items],
        "can_regenerate": used < sug_svc.MAX_REGENERATIONS,
        "regenerations_left": max(sug_svc.MAX_REGENERATIONS - used, 0),
    }


@router.post(
    "/assignments/{assignment_id}/suggestions/regenerate",
    response_model=RegenerateOut,
)
async def regenerate_suggestions(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    assignment: Assignment = Depends(get_current_santa),
) -> dict:
    room = await _room_for_assignment(db, assignment)
    used = await sug_svc.regenerations_used(db, assignment.id)
    if used >= sug_svc.MAX_REGENERATIONS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "REGENERATION_LIMIT",
                "message": f"Лимит перегенераций ({sug_svc.MAX_REGENERATIONS}) исчерпан",
            },
        )

    added = await sug_svc.regenerate(
        db, assignment, room.budget_min, room.budget_max,
    )
    await db.commit()

    used_after = await sug_svc.regenerations_used(db, assignment.id)
    stmt = (
        select(GiftSuggestion)
        .where(GiftSuggestion.assignment_id == assignment.id)
        .order_by(GiftSuggestion.score.desc().nulls_last())
    )
    all_items = list((await db.execute(stmt)).scalars().all())

    return {
        "assignment_id": assignment.id,
        "generation": used_after,
        "items": [_to_item(i) for i in all_items],
        "can_regenerate": used_after < sug_svc.MAX_REGENERATIONS,
        "regenerations_left": max(sug_svc.MAX_REGENERATIONS - used_after, 0),
        "added": len(added),
    }


# ---------------------------------------------------------------------------
# Статус подарка (Санта)
# ---------------------------------------------------------------------------

@router.patch(
    "/assignments/{assignment_id}/gift-status",
    response_model=GiftStatusUpdate,
)
async def update_gift_status(
    payload: GiftStatusUpdate,
    db: AsyncSession = Depends(get_db),
    assignment: Assignment = Depends(get_current_santa),
) -> dict:
    assignment.gift_status = payload.gift_status.value
    await db.commit()
    return {"gift_status": assignment.gift_status}


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

from app.models.santa import Draw  # добавить к импортам выше


async def _room_for_assignment(
    db: AsyncSession, assignment: Assignment
) -> Room:
    d = await db.get(Draw, assignment.draw_id)
    if d is None:
        raise HTTPException(status_code=404, detail={"code": "DRAW_NOT_FOUND"})
    room = await db.get(Room, d.room_id)
    if room is None:
        raise HTTPException(status_code=404, detail={"code": "ROOM_NOT_FOUND"})
    return room


def _to_item(s: GiftSuggestion) -> dict:
    return {
        "id": s.id,
        "external_id": s.external_id,
        "idea_title": s.idea_title,
        "category": s.category,
        "tags": list(s.tags or []),
        "price_min": s.price_min,
        "price_max": s.price_max,
        "reason": s.reason,
        "score": s.score,
        "source": s.source,
    }