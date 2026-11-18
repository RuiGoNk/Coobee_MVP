import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.santa import Notification
from app.models.user import User


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Типы уведомлений (для type в santa_notifications)
# ---------------------------------------------------------------------------

NT_INVITE = "santa_invite"
NT_JOINED = "santa_participant_joined"
NT_DRAW_DONE = "santa_draw_done"
NT_SUGGESTIONS_READY = "santa_suggestions_ready"
NT_NEW_MESSAGE = "santa_new_message"
NT_PROFILE_REMINDER = "santa_profile_reminder"
NT_SHIPPING_REMINDER = "santa_shipping_reminder"
NT_GIFT_SHIPPED = "santa_gift_shipped"


# ---------------------------------------------------------------------------
# Создание in-app уведомления
# ---------------------------------------------------------------------------

async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    type_: str,
    payload: dict[str, Any] | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        type=type_,
        payload=payload or {},
    )
    db.add(notif)
    await db.flush()
    return notif


# ---------------------------------------------------------------------------
# Отправка в Telegram (best-effort)
# ---------------------------------------------------------------------------

async def _send_telegram(telegram_id: int, text: str) -> None:
    """
    Отправляет сообщение через aiogram-бота.
    Импорт локальный — чтобы сервис не тянул aiogram, если бот не нужен.
    """
    try:
        from aiogram import Bot  # type: ignore
        from app.core.config import settings  # type: ignore

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        try:
            await bot.send_message(chat_id=telegram_id, text=text)
        finally:
            await bot.session.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram send failed: %s", exc)


# ---------------------------------------------------------------------------
# Композит: создать in-app + отправить в TG
# ---------------------------------------------------------------------------

async def notify_user(
    db: AsyncSession,
    user: User,
    type_: str,
    text: str,
    payload: dict[str, Any] | None = None,
) -> None:
    await create_notification(db, user.id, type_, payload)
    if user.telegram_id:
        await _send_telegram(user.telegram_id, text)

async def notify_invite(
    db: AsyncSession, user: User, room_title: str, deep_link: str
) -> None:
    await notify_user(
        db, user, NT_INVITE,
        f"Вас пригласили в «Тайный Санта»: {room_title}\n{deep_link}",
        {"room_title": room_title, "deep_link": deep_link},
    )


async def notify_joined(
    db: AsyncSession, organizer: User, participant_name: str, room_title: str
) -> None:
    await notify_user(
        db, organizer, NT_JOINED,
        f"{participant_name} присоединился к «{room_title}»",
        {"participant_name": participant_name},
    )


async def notify_draw_done(
    db: AsyncSession, user: User, room_title: str
) -> None:
    await notify_user(
        db, user, NT_DRAW_DONE,
        f"Жеребьёвка в «{room_title}» проведена. Откройте комнату, чтобы узнать подопечного.",
        {"room_title": room_title},
    )


async def notify_suggestions_ready(
    db: AsyncSession, user: User, room_title: str
) -> None:
    await notify_user(
        db, user, NT_SUGGESTIONS_READY,
        f"Идеи подарков для «{room_title}» готовы.",
        {"room_title": room_title},
    )


async def notify_new_message(
    db: AsyncSession, user: User, room_title: str, body_preview: str
) -> None:
    await notify_user(
        db, user, NT_NEW_MESSAGE,
        f"Новое сообщение от Санты в «{room_title}»: {body_preview}",
        {"room_title": room_title, "preview": body_preview},
    )


async def notify_profile_reminder(
    db: AsyncSession, user: User, room_title: str, days_left: int
) -> None:
    await notify_user(
        db, user, NT_PROFILE_REMINDER,
        f"Напоминание: заполните анкету в «{room_title}» (осталось {days_left} дн.).",
        {"room_title": room_title, "days_left": days_left},
    )


async def notify_shipping_reminder(
    db: AsyncSession, user: User, room_title: str, days_left: int
) -> None:
    await notify_user(
        db, user, NT_SHIPPING_REMINDER,
        f"Напоминание: отправьте подарок в «{room_title}» (осталось {days_left} дн.).",
        {"room_title": room_title, "days_left": days_left},
    )