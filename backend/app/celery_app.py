from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery = Celery(
    "coobee",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery.conf.timezone = "Europe/Moscow"
celery.conf.task_track_started = True

celery.conf.beat_schedule = {
    "gift-calendar-daily": {
        "task": "app.tasks.gift_calendar",
        "schedule": crontab(hour=10, minute=0),
    },
    "weekly-drop-thursday": {
        "task": "app.tasks.weekly_drop",
        "schedule": crontab(hour=10, minute=0, day_of_week=4),
    },
    # Ежедневно 10:00 MSK: напоминания 7/3/1 день (анкеты + отправка подарков).
    # santa_generate_suggestions в расписание НЕ ставим — запускается
    # по требованию из POST /draw через .delay().
    "santa-reminders-daily": {
        "task": "app.tasks.santa_reminders",
        "schedule": crontab(hour=10, minute=0),
    },
}

celery.autodiscover_tasks(["app"])