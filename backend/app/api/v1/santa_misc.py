"""
Роутер модуля santa: сообщения, дашборд, уведомления, GDPR.

Пути (под /api/v1/santa):
- POST   /assignments/{id}/messages        — анонимное сообщение паре
- GET    /assignments/{id}/messages        — история пары
- GET    /rooms/{id}/dashboard             — дашборд организатора (агрегаты)
- GET    /notifications                    — in-app центр (мои)
- PATCH  /notifications/{id}/read          — отметить прочитанным
- GET    /participants/me/export           — GDPR-экспорт (свои данные)

Критично:
- сообщения — только двум сторонам пары (get_assignment_for_pair_member);
- from_participant_id наружу НЕ отдаём (анонимизация, 3.4);
- дашборд — только агрегаты, без пар и подборок (FR-5.9, FR-7.3);
- GDPR-экспорт — только свои сообщения/уведомления.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_db
from app.models.santa import (
    Assignment,
    Draw,
    GiftSuggestion,
    Message,
    Notification,
    Participant,
    Room,
)
from app.models.user import User
from app.schemas.santa import (
    DashboardOut,
    DashboardParticipantStat,
    DrawOut,
    MessageCreate,
    MessageOut,
    NotificationOut,
    ParticipantExportOut,
)
from app.services.santa import notifications as notif
from app.services.santa.access import (
    get_assignment_for_pair_member,
    get_current_organizer,
    get_current_participant,
    get_latest_draw,
)


router = APIRouter(tags=["santa: messages, dashboard, notifications"])


# ---------------------------------------------------------------------------
# Сообщения (анонимный чат пары)
# ---------------------------------------------------------------------------

@router.post(
    "/assignments/{assignment_id}/messages",
    response_model=MessageOut,
)
async def send_message(
    assignment_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    assignment, santa, santee = await get_assignment_for_pair_member(
        assignment_id, db, user
    )

    # Кто пишет: Санта или подопечный?
    is_santa = user.id == santa.user_id
    to_participant = santee if is_santa else santa
    from_participant = santa if is_santa else santee

    room_id = await _room_id_for(db, assignment)

    msg = Message(
        room_id=room_id,
        assignment_id=assignment.id,
        from_participant_id=from_participant.id,
        to_participant_id=to_participant.id,
        body=payload.body,
        is_revealed=False,
    )
    db.add(msg)
    await db.flush()

    # Уведомление получателю (best-effort)
    to_user = await db.get(User, to_participant.user_id)
    room = await db.get(Room, room_id)
    if to_user and room:
        preview = payload.body[:80]
        await notif.notify_new_message(db, to_user, room.title, preview)

    await db.commit()
    await db.refresh(msg)

    return {
        "id": msg.id,
        "body": msg.body,
        "is_revealed": msg.is_revealed,
        "created_at": msg.created_at,
        "from_role": "santa" if is_santa else "santee",
    }


@router.get(
    "/assignments/{assignment_id}/messages",
    response_model=list[MessageOut],
)
async def list_messages(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    assignment, santa, santee = await get_assignment_for_pair_member(
        assignment_id, db, user
    )

    stmt = (
        select(Message)
        .where(Message.assignment_id == assignment_id)
        .order_by(Message.created_at.asc())
    )
    messages = list((await db.execute(stmt)).scalars().all())

    out: list[dict] = []
    for m in messages:
        # from_role определяем по тому, Санта это или подопечный.
        # from_participant_id наружу не отдаём (3.4).
        if m.from_participant_id == santa.id:
            role = "santa"
        else:
            role = "santee"
        out.append({
            "id": m.id,
            "body": m.body,
            "is_revealed": m.is_revealed,
            "created_at": m.created_at,
            "from_role": role,
        })
    return out


async def _room_id_for(db: AsyncSession, assignment: Assignment) -> uuid.UUID:
    d = await db.get(Draw, assignment.draw_id)
    if d is None:
        raise HTTPException(status_code=404, detail={"code": "DRAW_NOT_FOUND"})
    return d.room_id


# ---------------------------------------------------------------------------
# Дашборд организатора (только агрегаты)
# ---------------------------------------------------------------------------

@router.get("/rooms/{room_id}/dashboard", response_model=DashboardOut)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    room: Room = Depends(get_current_organizer),
) -> dict:
    # Участники
    p_stmt = select(Participant).where(Participant.room_id == room.id)
    participants = list((await db.execute(p_stmt)).scalars().all())

    total = len(participants)
    profile_min = sum(1 for p in participants if p.status == "profile_min")
    profile_full = sum(1 for p in participants if p.status == "profile_full")
    not_filled = sum(1 for p in participants if p.status == "joined")

    # Последний draw
    d = await get_latest_draw(db, room.id)
    draw_out = None
    if d:
        draw_out = {
            "id": d.id,
            "room_id": d.room_id,
            "drawn_at": d.drawn_at,
            "drawn_by": d.drawn_by,
            "algorithm_version": d.algorithm_version,
            "status": d.status,
        }

    # gift_status по участникам (если draw есть)
    gift_by_participant: dict[uuid.UUID, str] = {}
    if d:
        a_stmt = select(Assignment).where(Assignment.draw_id == d.id)
        for a in (await db.execute(a_stmt)).scalars().all():
            if a.santa_participant_id:
                gift_by_participant[a.santa_participant_id] = a.gift_status

    stat_list = [
        {
            "participant_id": p.id,
            "display_name": p.display_name,
            "status": p.status,
            "profile_completeness": p.profile_completeness,
            "is_deleted": p.is_deleted,
            "gift_status": gift_by_participant.get(p.id),
        }
        for p in participants
    ]

    return {
        "room_id": room.id,
        "room_status": room.status,
        "participants_total": total,
        "participants_profile_min": profile_min,
        "participants_profile_full": profile_full,
        "participants_not_filled": not_filled,
        "draw": draw_out,
        "participants": stat_list,
        # Без пар и подборок — только агрегаты (FR-5.9)
    }


# ---------------------------------------------------------------------------
# Уведомления in-app
# ---------------------------------------------------------------------------

@router.get("/notifications", response_model=list[NotificationOut])
async def list_my_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    return list((await db.execute(stmt)).scalars().all())


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Notification:
    n = await db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOTIFICATION_NOT_FOUND"},
        )
    from datetime import datetime, timezone
    n.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(n)
    return n


# ---------------------------------------------------------------------------
# GDPR-экспорт (свои данные)
# ---------------------------------------------------------------------------

@router.get(
    "/rooms/{room_id}/participants/me/export",
    response_model=ParticipantExportOut,
)
async def export_my_data(
    db: AsyncSession = Depends(get_db),
    participant: Participant = Depends(get_current_participant),
) -> dict:
    # Мои сообщения (только отправленные мной)
    m_stmt = (
        select(Message)
        .where(Message.from_participant_id == participant.id)
        .order_by(Message.created_at.asc())
    )
    messages = list((await db.execute(m_stmt)).scalars().all())

    msg_out = [
        {
            "id": m.id,
            "body": m.body,
            "is_revealed": m.is_revealed,
            "created_at": m.created_at,
            "from_role": "santa",  # мои сообщения — от меня
        }
        for m in messages
    ]

    # Мои уведомления
    n_stmt = (
        select(Notification)
        .where(Notification.user_id == participant.user_id)
        .order_by(Notification.created_at.desc())
    )
    notifications = list((await db.execute(n_stmt)).scalars().all())

    return {
        "participant": participant,
        "source_profile_snapshot": participant.source_profile_snapshot,
        "messages_sent": msg_out,
        "notifications": notifications,
    }