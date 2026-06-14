"""Точка входа бота."""

from __future__ import annotations

import logging

from telegram import BotCommand, Update
from telegram.ext import Application

from srblearn import db
from srblearn.config import Config, load_config
from srblearn.handlers import get_all_handlers
from srblearn.scheduler import setup_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand("start", "Приветствие и регистрация"),
    BotCommand("quiz", "Начать викторину"),
    BotCommand("settings", "Настройки уровня и уведомлений"),
    BotCommand("stats", "Статистика обучения"),
    BotCommand("help", "Справка по командам"),
]


async def post_init(application: Application) -> None:
    config: Config = application.bot_data["config"]
    await db.init_db(config.db_path)
    await setup_scheduler(application, config.db_path)
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("SrbLearn bot started (db: %s)", config.db_path)


async def post_shutdown(application: Application) -> None:
    scheduler = application.bot_data.get("notification_scheduler")
    if scheduler is not None:
        scheduler.shutdown()
        logger.info("Notification scheduler stopped")


def build_application(config: Config) -> Application:
    application = (
        Application.builder()
        .token(config.bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    application.bot_data["config"] = config
    application.bot_data["db_path"] = config.db_path

    for handler in get_all_handlers():
        application.add_handler(handler)

    return application


def main() -> None:
    config = load_config()
    application = build_application(config)
    logger.info("Starting polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
