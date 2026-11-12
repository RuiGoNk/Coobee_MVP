"""
Жеребьёвка модуля santa.

Алгоритм (FR-4):
- случайная перестановка без неподвижных точек (никто не дарит себе);
- учёт Exclusion (запрещённые пары A≠B, симметрично);
- опция "цепочка" (A→B→C→A) vs полностью случайная;
- проверка разрешимости → DRAW_INFEASIBLE;
- результат сохраняется в БД, доступ к паре — только двум сторонам.

Генерация подборок — НЕ здесь. После draw ставим Draw.status='generating'
и отправляем Celery-таск (Шаг 6), который сгенерирует GiftSuggestion
и переведёт статус в 'ready'.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.santa import (
    Assignment,
    Draw,
    Exclusion,
    Participant,
    Room,
)


# ---------------------------------------------------------------------------
# Ошибки
# ---------------------------------------------------------------------------

def _infeasible(details: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "DRAW_INFEASIBLE",
            "message": "Невозможно провести жеребьёвку с текущими ограничениями",
            "details": details or {},
        },
    )


# ---------------------------------------------------------------------------
# Загрузка данных
# ---------------------------------------------------------------------------

async def load_participants(
    db: AsyncSession, room_id: uuid.UUID
) -> list[Participant]:
    stmt = select(Participant).where(
        Participant.room_id == room_id,
        Participant.is_deleted.is_(False),
    )
    return list((await db.execute(stmt)).scalars().all())


async def load_exclusions(
    db: AsyncSession, room_id: uuid.UUID
) -> set[frozenset[uuid.UUID]]:
    """
    Множество запрещённых пар (симметрично): frozenset({a, b}).
    """
    stmt = select(Exclusion).where(Exclusion.room_id == room_id)
    rows = (await db.execute(stmt)).scalars().all()
    return {frozenset({e.participant_a_id, e.participant_b_id}) for e in rows}


# ---------------------------------------------------------------------------
# Проверка разрешимости (необходимое условие)
# ---------------------------------------------------------------------------

def check_feasibility(
    participant_ids: list[uuid.UUID],
    exclusions: set[frozenset[uuid.UUID]],
) -> None:
    """
    Быстрая проверка:
    - минимум 3 участника (FR-4.4);
    - для каждого участника есть хотя бы один допустимый получатель
      (не себя, не в exclusion).

    Точная проверка (существование гамильтонова цикла/перестановки) —
    в самом алгоритме; здесь отсекаем очевидные тупики.
    """
    n = len(participant_ids)
    if n < 3:
        raise _infeasible({"reason": "too_few_participants", "count": n})

    for pid in participant_ids:
        allowed = [
            other for other in participant_ids
            if other != pid and frozenset({pid, other}) not in exclusions
        ]
        if not allowed:
            raise _infeasible(
                {"reason": "no_valid_target", "participant_id": str(pid)}
            )


# ---------------------------------------------------------------------------
# Случайная перестановка без неподвижных точек + exclusions
# ---------------------------------------------------------------------------

def _random_derangement(
    participant_ids: list[uuid.UUID],
    exclusions: set[frozenset[uuid.UUID]],
    rng: random.Random,
    max_attempts: int = 1000,
) -> dict[uuid.UUID, uuid.UUID]:
    """
    Возвращает {santa_id: santee_id}.
    Пробует случайные перестановки, отбрасывает неподвижные точки и exclusions.
    При n ≤ 30 вероятность успеха высокая; max_attempts — защита.
    """
    n = len(participant_ids)

    for _ in range(max_attempts):
        shuffled = participant_ids.copy()
        rng.shuffle(shuffled)
        mapping: dict[uuid.UUID, uuid.UUID] = {}
        ok = True

        for santa, santee in zip(participant_ids, shuffled):
            if santa == santee:
                ok = False
                break
            if frozenset({santa, santee}) in exclusions:
                ok = False
                break
            mapping[santa] = santee

        if ok and len(mapping) == n:
            return mapping

    raise _infeasible({"reason": "no_derangement_found", "attempts": max_attempts})


# ---------------------------------------------------------------------------
# Цепочка A→B→C→A
# ---------------------------------------------------------------------------

def _chain(
    participant_ids: list[uuid.UUID],
    exclusions: set[frozenset[uuid.UUID]],
    rng: random.Random,
    max_attempts: int = 1000,
) -> dict[uuid.UUID, uuid.UUID]:
    """
    Строит одну цепочку-цикл, проходящую через всех участников,
    без нарушения exclusions. Пробует случайные перестановки.
    """
    n = len(participant_ids)

    for _ in range(max_attempts):
        order = participant_ids.copy()
        rng.shuffle(order)
        mapping: dict[uuid.UUID, uuid.UUID] = {}
        ok = True

        for i in range(n):
            santa = order[i]
            santee = order[(i + 1) % n]
            if frozenset({santa, santee}) in exclusions:
                ok = False
                break
            mapping[santa] = santee

        if ok and len(mapping) == n:
            return mapping

    raise _infeasible({"reason": "no_chain_found", "attempts": max_attempts})


# ---------------------------------------------------------------------------
# Главная функция: создать Draw + Assignment
# ---------------------------------------------------------------------------

async def run_draw(
    db: AsyncSession,
    room: Room,
    drawn_by: uuid.UUID,
    mode: str = "random",
    seed: int | None = None,
) -> Draw:
    """
    Проводит жеребьёвку, сохраняет Draw + Assignment.
    НЕ генерирует подборки — это делает Celery после коммита.

    Возвращает Draw со статусом 'generating'.
    """
    participants = await load_participants(db, room.id)
    participant_ids = [p.id for p in participants]
    exclusions = await load_exclusions(db, room.id)

    check_feasibility(participant_ids, exclusions)

    rng = random.Random(seed) if seed is not None else random.Random()

    if mode == "chain":
        mapping = _chain(participant_ids, exclusions, rng)
    else:
        mapping = _random_derangement(participant_ids, exclusions, rng)

    # Создаём Draw
    draw = Draw(
        room_id=room.id,
        drawn_by=drawn_by,
        drawn_at=datetime.now(timezone.utc),
        algorithm_version=f"v1_{mode}",
        status="generating",
    )
    db.add(draw)
    await db.flush()  # получить draw.id

    # Создаём Assignment
    for santa_id, santee_id in mapping.items():
        db.add(
            Assignment(
                draw_id=draw.id,
                santa_participant_id=santa_id,
                santee_participant_id=santee_id,
                gift_status="pending",
            )
        )

    # Меняем статус комнаты
    room.status = "drawn"

    await db.flush()
    return draw


# ---------------------------------------------------------------------------
# Пережеребьёвка: проверка, что можно
# ---------------------------------------------------------------------------

async def ensure_redraw_allowed(
    db: AsyncSession,
    room: Room,
) -> None:
    """
    Пережеребьёвка разрешена, только если никто ещё не смотрел результат
    (FR-4.9). Иначе — 409 с требованием подтверждения.
    """
    stmt = select(Assignment).join(Draw).where(
        Draw.room_id == room.id,
        Assignment.viewed_at.is_not(None),
    )
    viewed = (await db.execute(stmt)).scalars().first()
    if viewed is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REDRAW_REQUIRES_CONFIRMATION",
                "message": (
                    "Кто-то уже просмотрел результат жеребьёвки. "
                    "Пережеребьёвка возможна только с подтверждением "
                    "и уведомлением всех участников."
                ),
            },
        )