import asyncio
from datetime import date, datetime, timedelta

from aiogram import Bot
from sqlalchemy import select

from app.celery_app import celery
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.catalog import CatalogItem
from app.models.feedback import Feedback
from app.models.recipient import Recipient
from app.models.user import User, UserProfile

def _new_bot() -> Bot:
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)


def _run(coro):
    return asyncio.run(coro)


async def _send(telegram_id: int, text: str) -> None:
    bot = _new_bot()
    try:
        await bot.send_message(telegram_id, text)
    except Exception as e:  # noqa: BLE001
        print(f"send error to {telegram_id}: {type(e).__name__}: {e}")
    finally:
        await bot.session.close()


# ---------- Gift Calendar ----------
def _days_until(month: int, day: int, today: date) -> int:
    target = date(today.year, month, day)
    if target < today:
        target = date(today.year + 1, month, day)
    return (target - today).days


async def _gift_calendar() -> None:
    today = date.today()
    window = 14
    async with SessionLocal() as db:
        stmt = select(Recipient).where(
            Recipient.is_deleted.is_(False),
            Recipient.notifications_enabled.is_(True),
        )
        recipients = (await db.execute(stmt)).scalars().all()

        for rec in recipients:
            user = await db.get(User, rec.user_id)
            if not user:
                continue

            reasons: list[str] = []

            # ДР
            if rec.birth_date:
                d = _days_until(rec.birth_date.month, rec.birth_date.day, today)
                if d == window:
                    reasons.append("день рождения")

            # Новый год (31.12)
            if _days_until(12, 31, today) == window:
                reasons.append("Новый год")

            # 8 марта
            if rec.gender in ("female", "unisex") and _days_until(3, 8, today) == window:
                reasons.append("8 марта")

            # 23 февраля
            if rec.gender in ("male", "unisex") and _days_until(2, 23, today) == window:
                reasons.append("23 февраля")

            if reasons:
                what = " и ".join(reasons)
                text = f"У «{rec.name}» скоро {what}. Начать подбор подарка? → {settings.APP_DOMAIN}"
                await _send(user.telegram_id, text)


@celery.task(name="app.tasks.gift_calendar")
def gift_calendar() -> None:
    _run(_gift_calendar())


# ---------- Weekly Drop ----------
async def _weekly_drop() -> None:
    async with SessionLocal() as db:
        users_stmt = select(User)
        users = (await db.execute(users_stmt)).scalars().all()

        for user in users:
            liked_stmt = select(Feedback.item_id).where(
                Feedback.user_id == user.id,
                Feedback.action == "like",
            )
            liked_ids = set((await db.execute(liked_stmt)).scalars().all())

            prof_stmt = select(UserProfile).where(UserProfile.user_id == user.id)
            profile = (await db.execute(prof_stmt)).scalar_one_or_none()
            interests = set(profile.interests or []) if profile else set()

            items_stmt = select(CatalogItem).where(CatalogItem.is_available.is_(True))
            all_items = [it for it in (await db.execute(items_stmt)).scalars().all() if it.id not in liked_ids]
            if not all_items:
                continue
            ranked = sorted(all_items, key=lambda it: len(set(it.tags or []) & interests), reverse=True)[:5]
            if not ranked:
                continue
            lines = "\n".join(f"• {it.title} ({it.price_min}–{it.price_max} ₽)" for it in ranked)
            text = f"Еженедельная подборка подарков:\n{lines}\n\nСмотреть на сайте → {settings.APP_DOMAIN}"
            await _send(user.telegram_id, text)


@celery.task(name="app.tasks.weekly_drop")
def weekly_drop() -> None:
    _run(_weekly_drop())


# ===========================================================================
# Santa module
# ===========================================================================

async def _santa_generate_suggestions(draw_id) -> None:
    """
    Генерация подборок для всех assignment конкретного draw.
    Вызывается из Celery после POST /draw.
    """
    import uuid as _uuid

    from app.services.santa.generation import generate_for_draw

    if isinstance(draw_id, str):
        draw_id = _uuid.UUID(draw_id)

    async with SessionLocal() as db:
        try:
            count = await generate_for_draw(db, draw_id, send_notifications=True)
            await db.commit()
            print(f"santa_generate_suggestions draw={draw_id} created={count}")
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            print(f"santa_generate_suggestions error: {type(exc).__name__}: {exc}")
            raise


@celery.task(name="app.tasks.santa_generate_suggestions")
def santa_generate_suggestions(draw_id: str) -> None:
    _run(_santa_generate_suggestions(draw_id))


# ---------------------------------------------------------------------------
# Напоминания 7/3/1 день (анкеты и отправка подарков)
# ---------------------------------------------------------------------------

_PROFILE_REMINDER_OFFSET_DAYS = 7
_REMINDER_THRESHOLDS = {7, 3, 1}


async def _santa_reminders() -> None:
    """
    Для каждой активной комнаты:
    - до дедлайна анкет (event_date - 7 дней): 7/3/1 → напомнить без profile_full;
    - до дедлайна отправки (event_date): 7/3/1 → напомнить Сантам с gift_status='pending'.

    Если в Room появятся отдельные дедлайны — заменить эвристику.
    """
    from datetime import timedelta

    from app.models.santa import Assignment, Draw, Participant, Room
    from app.services.santa import notifications as notif

    today = date.today()

    async with SessionLocal() as db:
        try:
            rooms_stmt = select(Room).where(
                Room.status.in_(("collecting", "drawn", "in_progress"))
            )
            rooms = (await db.execute(rooms_stmt)).scalars().all()

            for room in rooms:
                if room.event_date is None:
                    continue

                profile_deadline = room.event_date - timedelta(
                    days=_PROFILE_REMINDER_OFFSET_DAYS
                )
                shipping_deadline = room.event_date

                days_to_profile = (profile_deadline - today).days
                days_to_shipping = (shipping_deadline - today).days

                if days_to_profile in _REMINDER_THRESHOLDS:
                    await _santa_remind_profiles(db, room, days_to_profile, notif)

                if days_to_shipping in _REMINDER_THRESHOLDS:
                    await _santa_remind_shipping(db, room, days_to_shipping, notif)

            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            print(f"santa_reminders error: {type(exc).__name__}: {exc}")
            raise


async def _santa_remind_profiles(db, room, days_left: int, notif) -> None:
    from app.models.santa import Participant

    stmt = select(Participant).where(
        Participant.room_id == room.id,
        Participant.is_deleted.is_(False),
        Participant.status.in_(("joined", "profile_min")),
    )
    for p in (await db.execute(stmt)).scalars().all():
        user = await db.get(User, p.user_id)
        if user:
            await notif.notify_profile_reminder(db, user, room.title, days_left)


async def _santa_remind_shipping(db, room, days_left: int, notif) -> None:
    from app.models.santa import Assignment, Draw, Participant

    d_stmt = (
        select(Draw)
        .where(Draw.room_id == room.id)
        .order_by(Draw.drawn_at.desc())
        .limit(1)
    )
    d = (await db.execute(d_stmt)).scalar_one_or_none()
    if d is None:
        return

    a_stmt = select(Assignment).where(
        Assignment.draw_id == d.id,
        Assignment.gift_status == "pending",
    )
    for a in (await db.execute(a_stmt)).scalars().all():
        if a.santa_participant_id is None:
            continue
        santa = await db.get(Participant, a.santa_participant_id)
        if santa is None:
            continue
        user = await db.get(User, santa.user_id)
        if user:
            await notif.notify_shipping_reminder(db, user, room.title, days_left)


@celery.task(name="app.tasks.santa_reminders")
def santa_reminders() -> None:
    _run(_santa_reminders())
