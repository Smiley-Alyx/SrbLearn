"""Обработчик /start, /help, /stats."""

from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from srblearn import db
from srblearn.handlers.common import get_db_path, inline_keyboard, level_keyboard

WELCOME_TEXT = (
    "👋 Добро пожаловать в *SrbLearn*!\n\n"
    "Бот поможет изучать сербский язык с интервальным повторением.\n\n"
    "Основные команды:\n"
    "/quiz — начать викторину\n"
    "/settings — настройки уровня и уведомлений\n"
    "/stats — ваша статистика\n"
    "/help — справка"
)

HELP_TEXT = (
    "📖 *Справка SrbLearn*\n\n"
    "/start — приветствие и регистрация\n"
    "/quiz — викторина (сербский→русский или русский→сербский)\n"
    "/settings — уровень A1–C2, уведомления, время напоминаний\n"
    "/stats — изучено слов, точность, слова на повторении\n"
    "/help — эта справка\n\n"
    "Словари редактируются через файлы vocabulary/*.json."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    db_path = get_db_path(context)

    existing = await db.get_user(db_path, user_id)
    user = await db.get_or_create_user(db_path, user_id, username)

    await update.message.reply_text(WELCOME_TEXT, parse_mode="Markdown")

    if existing is None:
        keyboard = inline_keyboard(level_keyboard("start:level"))
        await update.message.reply_text(
            "Вы новый пользователь. Выберите уровень для начала:",
            reply_markup=keyboard,
        )
    else:
        await update.message.reply_text(
            f"Ваш текущий уровень: *{user.level}*. Удачной учёбы!",
            parse_mode="Markdown",
        )


async def start_level_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None or query.data is None or update.effective_user is None:
        return

    await query.answer()
    level = query.data.split(":")[-1]
    db_path = get_db_path(context)

    await db.update_user_level(db_path, update.effective_user.id, level)
    await query.edit_message_text(
        f"✅ Уровень *{level}* сохранён. Нажмите /quiz, чтобы начать!",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    db_path = get_db_path(context)
    user = await db.get_or_create_user(
        db_path,
        update.effective_user.id,
        update.effective_user.username,
    )
    stats = await db.get_user_stats(db_path, user.user_id, user.level)

    await update.message.reply_text(
        f"📊 *Статистика* (уровень {user.level})\n\n"
        f"Слов изучено: {stats.words_learned}\n"
        f"Всего ответов: {stats.total_answers}\n"
        f"Правильных: {stats.correct_answers}\n"
        f"Точность: {stats.accuracy:.1f}%\n"
        f"На повторении: {stats.words_due}",
        parse_mode="Markdown",
    )


def get_handlers() -> list:
    return [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("stats", stats_command),
        CallbackQueryHandler(start_level_callback, pattern=r"^start:level:"),
    ]
