"""APScheduler: отправка уведомлений."""

from __future__ import annotations

import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.ext import Application

from srblearn import db

logger = logging.getLogger(__name__)

NOTIFICATION_TEXT = "🔔 Время повторить сербские слова! Нажми /quiz"


def parse_notify_time(time_str: str) -> tuple[int, int]:
    hour_str, minute_str = time_str.split(":")
    return int(hour_str), int(minute_str)


def job_id(user_id: int, slot: int) -> str:
    return f"notify_{user_id}_{slot}"


class NotificationScheduler:
    """Планировщик напоминаний о повторении слов."""

    def __init__(self, db_path: Path, bot: Bot) -> None:
        self.db_path = db_path
        self.bot = bot
        self._scheduler = AsyncIOScheduler()

    async def send_notification(self, user_id: int) -> None:
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=NOTIFICATION_TEXT,
            )
        except Exception:
            logger.exception("Failed to send notification to user %s", user_id)

    def remove_user_jobs(self, user_id: int) -> None:
        prefix = f"notify_{user_id}_"
        for job in self._scheduler.get_jobs():
            if job.id.startswith(prefix):
                job.remove()

    async def refresh_user(self, user_id: int) -> None:
        """Пересоздать jobs для пользователя после изменения настроек."""
        self.remove_user_jobs(user_id)

        user = await db.get_user(self.db_path, user_id)
        if user is None or not user.notifications_enabled:
            return

        times = user.notify_times[: user.notify_count]
        for slot, time_str in enumerate(times):
            hour, minute = parse_notify_time(time_str)
            self._scheduler.add_job(
                self.send_notification,
                CronTrigger(hour=hour, minute=minute),
                args=[user_id],
                id=job_id(user_id, slot),
                replace_existing=True,
            )
            logger.info(
                "Scheduled notification for user %s at %02d:%02d (slot %d)",
                user_id,
                hour,
                minute,
                slot,
            )

    async def restore_all(self) -> None:
        """Восстановить расписание для всех пользователей из БД."""
        users = await db.get_users_with_notifications(self.db_path)
        for user in users:
            await self.refresh_user(user.user_id)
        logger.info("Restored notifications for %d users", len(users))

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)


async def setup_scheduler(application: Application, db_path: Path) -> NotificationScheduler:
    """Инициализировать планировщик и зарегистрировать хук в bot_data."""
    scheduler = NotificationScheduler(db_path, application.bot)
    application.bot_data["notification_scheduler"] = scheduler
    application.bot_data["refresh_user_notifications"] = scheduler.refresh_user

    await scheduler.restore_all()
    scheduler.start()
    return scheduler
