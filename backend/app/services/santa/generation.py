"""
Фоновая генерация подборок после жеребьёвки.

Используется:
- из Celery-таска santa_generate_suggestions (прод);
- из роутера start_draw как fallback, если Celery не настроен (MVP).

После генерации: Draw.status = 'ready', Room.status = 'in_progress',
участникам уходит уведомление suggestions_ready.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.santa import Assignment, Draw, Participant, Room
from app.models.user import User
from app.services.santa import notifications as notif
from app.services.santa import suggestions as sug_svc


logger = logging.getLogger(__name__)


async def generate_for_draw(
    db: AsyncSession,
    draw_id: uuid.UUID,
    send_notifications: bool = True,
) -> int:
    """
    Генерирует подборки для всех assignment этого draw.
    Возвращает количество созданных GiftSuggestion.
    """
    d = await db.get(Draw, draw_id)
    if d is None:
        logger.warning("generate_for_draw: draw %s not found", draw_id)
        return 0

    room = await db.get(Room, d.room_id)
    if room is None:
        logger.warning("generate_for_draw: room for draw %s not found", draw_id)
        return 0

    stmt = select(Assignment).where(Assignment.draw_id == d.id)
    assignments = list((await db.execute(stmt)).scalars().all())

    total_created = 0
    for a in assignments:
        created = await sug_svc.generate_first_batch(
            db, a, room.budget_min, room.budget_max,
        )
        total_created += len(created)

    d.status = "ready"
    room.status = "in_progress"
    await db.flush()

    if send_notifications:
        await _notify_participants(db, room, assignments)

    return total_created


async def _notify_participants(
    db: AsyncSession,
    room: Room,
    assignments: list[Assignment],
) -> None:
    """
    Уведомляет каждого Санту: «идеи готовы».
    Best-effort: ошибки логируются, не ломают генерацию.
    """
    for a in assignments:
        if a.santa_participant_id is None:
            continue
        santa = await db.get(Participant, a.santa_participant_id)
        if santa is None or santa.is_deleted:
            continue
        user = await db.get(User, santa.user_id)
        if user is None:
            continue
        try:
            await notif.notify_suggestions_ready(db, user, room.title)
        except Exception as exc:  # noqa: BLE001
            logger.warning("notify_suggestions_ready failed: %s", exc)