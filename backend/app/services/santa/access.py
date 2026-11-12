"""
Проверки доступа модуля santa.

Критично:
- подборка доступна ТОЛЬКО Санте для своего assignment;
- получатель, организатор, третьи лица → 403;
- организатор видит только агрегаты дашборда, не подборки и не пары.

Все проверки — на уровне dependency, не в бизнес-логике.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_db
from app.models.santa import Assignment, Draw, Participant, Room
from app.models.user import User


# ---------------------------------------------------------------------------
# Ошибки
# ---------------------------------------------------------------------------

def _forbidden(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": code, "message": message},
    )


def _not_found(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": code, "message": message},
    )


# ---------------------------------------------------------------------------
# Базовые выборки
# ---------------------------------------------------------------------------

async def get_room_or_404(db: AsyncSession, room_id: uuid.UUID) -> Room:
    room = await db.get(Room, room_id)
    if room is None:
        raise _not_found("ROOM_NOT_FOUND", "Комната не найдена")
    return room


async def get_participant_in_room(
    db: AsyncSession,
    room_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Participant | None:
    stmt = select(Participant).where(
        Participant.room_id == room_id,
        Participant.user_id == user_id,
        Participant.is_deleted.is_(False),
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_assignment_or_404(
    db: AsyncSession, assignment_id: uuid.UUID
) -> Assignment:
    assignment = await db.get(Assignment, assignment_id)
    if assignment is None:
        raise _not_found("ASSIGNMENT_NOT_FOUND", "Назначение не найдено")
    return assignment


# ---------------------------------------------------------------------------
# Участник комнаты (любой)
# ---------------------------------------------------------------------------

async def get_current_participant(
    room_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> Participant:
    participant = await get_participant_in_room(db, room_id, user.id)
    if participant is None:
        raise _forbidden("NOT_IN_ROOM", "Вы не участник этой комнаты")
    return participant


# ---------------------------------------------------------------------------
# Организатор комнаты
# ---------------------------------------------------------------------------

async def get_current_organizer(
    room_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> Room:
    room = await get_room_or_404(db, room_id)
    if room.owner_id != user.id:
        raise _forbidden("NOT_ORGANIZER", "Только организатор комнаты")
    return room


# ---------------------------------------------------------------------------
# Санта для assignment — ЯДРО ПРИВАТНОСТИ
# ---------------------------------------------------------------------------

async def get_current_santa(
    assignment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> Assignment:
    """
    Возвращает Assignment, только если текущий пользователь —
    Санта для этого assignment. Иначе 403.

    Получатель (santee) → 403.
    Организатор (owner комнаты) → 403 (видит только агрегаты дашборда).
    Третьи лица → 403.
    """
    assignment = await get_assignment_or_404(db, assignment_id)

    # assignment мог быть анонимизирован (GDPR hard-delete, 3.8)
    if assignment.santa_participant_id is None:
        raise _forbidden("ASSIGNMENT_ANONYMIZED", "Назначение недоступно")

    santa = await db.get(Participant, assignment.santa_participant_id)
    if santa is None or santa.is_deleted:
        raise _forbidden("SANTA_DELETED", "Участник удалён")

    if santa.user_id != user.id:
        # Не раскрываем, кто получатель/Санта — просто 403
        raise _forbidden(
            "SUGGESTIONS_FORBIDDEN",
            "Доступ к подборке есть только у Санты для этого получателя",
        )

    return assignment


# ---------------------------------------------------------------------------
# Пара «Санта ↔ Подопечный» (для чата)
# ---------------------------------------------------------------------------

async def get_assignment_for_pair_member(
    assignment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> tuple[Assignment, Participant, Participant]:
    """
    Возвращает (assignment, santa, santee), если текущий user —
    одна из двух сторон пары. Иначе 403.
    Используется для чата (обе стороны).
    """
    assignment = await get_assignment_or_404(db, assignment_id)

    if (
        assignment.santa_participant_id is None
        or assignment.santee_participant_id is None
    ):
        raise _forbidden("ASSIGNMENT_ANONYMIZED", "Назначение недоступно")

    santa = await db.get(Participant, assignment.santa_participant_id)
    santee = await db.get(Participant, assignment.santee_participant_id)
    if santa is None or santee is None:
        raise _forbidden("ASSIGNMENT_BROKEN", "Назначение повреждено")

    if user.id not in (santa.user_id, santee.user_id):
        raise _forbidden("NOT_IN_PAIR", "Вы не участник этой пары")

    return assignment, santa, santee


# ---------------------------------------------------------------------------
# Организатор может настраивать комнату только до жеребьёвки
# (после — только с подтверждением, FR-1.5)
# ---------------------------------------------------------------------------

async def ensure_room_editable(db: AsyncSession, room: Room) -> None:
    if room.status in ("drawn", "in_progress", "completed", "archived"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ROOM_LOCKED",
                "message": "Настройки комнаты заблокированы после жеребьёвки",
                "details": {"status": room.status},
            },
        )


async def ensure_draw_possible(
    db: AsyncSession, room: Room
) -> None:
    """Проверка, что жеребьёвку можно запускать (статус + участники)."""
    if room.status not in ("collecting",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DRAW_NOT_ALLOWED",
                "message": "Жеребьёвка возможна только в статусе collecting",
                "details": {"status": room.status},
            },
        )

    stmt = select(Participant).where(
        Participant.room_id == room.id,
        Participant.is_deleted.is_(False),
    )
    participants = (await db.execute(stmt)).scalars().all()

    if len(participants) < 3:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DRAW_TOO_FEW_PARTICIPANTS",
                "message": "Для жеребьёвки нужно минимум 3 участника",
                "details": {"count": len(participants)},
            },
        )

    if len(participants) > room.max_participants:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DRAW_TOO_MANY_PARTICIPANTS",
                "message": f"Максимум {room.max_participants} участников",
                "details": {"count": len(participants), "max": room.max_participants},
            },
        )

    # Проверка, что все заполнили мини-анкету (если require_min_profile)
    if room.require_min_profile:
        not_ready = [
            p.display_name
            for p in participants
            if p.status not in ("profile_min", "profile_full")
        ]
        if not_ready:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DRAW_PROFILES_INCOMPLETE",
                    "message": "Не все участники заполнили мини-анкету",
                    "details": {"participants": not_ready},
                },
            )


# ---------------------------------------------------------------------------
# Утилита: достать Draw комнаты
# ---------------------------------------------------------------------------

async def get_latest_draw(db: AsyncSession, room_id: uuid.UUID) -> Draw | None:
    stmt = (
        select(Draw)
        .where(Draw.room_id == room_id)
        .order_by(Draw.drawn_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()