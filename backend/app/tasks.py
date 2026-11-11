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
