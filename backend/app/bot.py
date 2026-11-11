import asyncio
import uuid
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.auth_session import AuthSession
from app.models.user import User

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


async def get_or_create_user(db: AsyncSession, tg_id: int, username: str | None) -> User:
    stmt = select(User).where(User.telegram_id == tg_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        user = User(telegram_id=tg_id, username=username)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@dp.message(CommandStart(deep_link=True))
async def start_with_deeplink(message: Message, command: CommandObject):
    payload = command.args or ""
    if not payload.startswith("auth_"):
        await message.answer("Привет! Открой сайт CooBee и нажми «Войти через Telegram».")
        return

    raw_id = payload.removeprefix("auth_")
    try:
        sess_id = uuid.UUID(raw_id)
    except ValueError:
        await message.answer("Ссылка входа недействительна. Попробуй ещё раз с сайта.")
        return

    async with SessionLocal() as db:
        sess = await db.get(AuthSession, sess_id)
        if not sess:
            await message.answer("Сессия входа не найдена. Попробуй ещё раз с сайта.")
            return
        if sess.expires_at < datetime.now(timezone.utc):
            await message.answer("Сессия входа истекла. Попробуй ещё раз с сайта.")
            return

        user = await get_or_create_user(db, message.from_user.id, message.from_user.username)
        sess.status = "confirmed"
        sess.user_id = user.id
        await db.commit()

    await message.answer("✅ Вход подтверждён. Вернись на сайт — там ты уже авторизован.")


@dp.message(CommandStart())
async def start_plain(message: Message):
    await message.answer("Привет! Открой сайт CooBee и нажми «Войти через Telegram».")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())