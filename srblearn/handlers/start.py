"""Обработчик /start, /help, /stats."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
)

from srblearn import db
from srblearn.handlers.common import (
    BTN_HELP_FILTER,
    BTN_STATS_FILTER,
    get_db_path,
    inline_keyboard,
    level_keyboard,
    main_menu_keyboard,
    script_keyboard_markup,
)
from srblearn.level_advice import get_level_recommendation
from srblearn.script_prefs import script_label
from srblearn.vocabulary import word_count

WELCOME_TEXT = (
    "👋 Добро пожаловать в *SrbLearn*!\n\n"
    "Изучайте сербские слова через викторину с интервальным повторением *(SM-2)*.\n\n"
    "*Как это работает:*\n"
    "1️⃣ Выберите уровень *A1–C2* под ваши знания\n"
    "2️⃣ Проходите викторину — слово и 4 варианта ответа\n"
    "3️⃣ Бот запоминает ошибки и напоминает повторить вовремя\n"
    "4️⃣ Включите уведомления — бот сам позовёт на повторение\n\n"
    "Управляйте ботом кнопками меню ниже 👇"
)

HELP_TEXT = (
    "📖 *Как пользоваться SrbLearn*\n\n"
    "*Викторина* 📝\n"
    "Два режима: сербский → русский и русский → сербский. "
    "После каждого ответа бот показывает результат и предлагает следующее слово.\n\n"
    "*Интервальное повторение* 🧠\n"
    "Алгоритм SM-2 подстраивает интервалы: правильные ответы увеличивают паузу, "
    "ошибки возвращают слово в приоритетную очередь.\n\n"
    "*Уровни* 📚\n"
    "A1 — базовая лексика, C2 — редкие и специализированные слова. "
    "Всего 3000+ слов по уровням CEFR.\n\n"
    "*Настройки* ⚙️\n"
    "Уровень, алфавит (кириллица / латиница), уведомления (1–3 раза в сутки), "
    "время напоминаний в формате HH:MM.\n\n"
    "*Статистика* 📊\n"
    "Изучено слов, точность ответов, сколько слов ждут повторения.\n\n"
    "*Поддержка* 💬\n"
    "Команда /support — отправить багрепорт, пожелание или вопрос.\n\n"
    "Кнопки меню: 📝 Викторина · ⚙️ Настройки · 📊 Статистика · ❓ Справка"
)


async def send_help(update: Update) -> None:
    message = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if message is not None:
        await message.reply_text(HELP_TEXT, parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def send_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None:
        return

    message = update.message
    if message is None:
        return

    db_path = get_db_path(context)
    user = await db.get_or_create_user(
        db_path,
        update.effective_user.id,
        update.effective_user.username,
    )
    stats = await db.get_user_stats(db_path, user.user_id, user.level)
    recommendation = get_level_recommendation(
        user.level,
        stats,
        word_count(user.level),
    )

    await message.reply_text(
        f"📊 *Статистика* (уровень {user.level})\n\n"
        f"Слов изучено: {stats.words_learned}\n"
        f"Всего ответов: {stats.total_answers}\n"
        f"Правильных: {stats.correct_answers}\n"
        f"Точность: {stats.accuracy:.1f}%\n"
        f"На повторении: {stats.words_due}\n\n"
        f"{recommendation}",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    db_path = get_db_path(context)

    existing = await db.get_user(db_path, user_id)
    user = await db.get_or_create_user(db_path, user_id, username)

    help_inline = inline_keyboard([[("❓ Как это работает?", "menu:help")]])
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    await update.message.reply_text(
        "Нужна подсказка? Нажмите кнопку ниже или *❓ Справка* в меню.",
        parse_mode="Markdown",
        reply_markup=help_inline,
    )

    if existing is None:
        keyboard = inline_keyboard(level_keyboard("start:level"))
        await update.message.reply_text(
            "Вы новый пользователь — выберите уровень для начала:",
            reply_markup=keyboard,
        )
    else:
        await update.message.reply_text(
            f"Ваш уровень: *{user.level}*, алфавит: *{script_label(user.script)}*. "
            f"Нажмите 📝 *Викторина*, чтобы начать!",
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
    context.user_data["pending_level"] = level

    await query.edit_message_text(
        f"Уровень: *{level}*\n\nВыберите алфавит для сербских слов:",
        reply_markup=script_keyboard_markup("start:script"),
        parse_mode="Markdown",
    )


async def start_script_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None or query.data is None or update.effective_user is None:
        return

    await query.answer()
    script = query.data.split(":")[-1]
    level = context.user_data.pop("pending_level", "A1")
    db_path = get_db_path(context)

    await db.update_user_level(db_path, update.effective_user.id, level)
    await db.update_user_script(db_path, update.effective_user.id, script)
    await query.edit_message_text(
        f"✅ Уровень *{level}*, алфавит: *{script_label(script)}*.\n"
        f"Нажмите 📝 *Викторина*, чтобы начать!",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_help(update)


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    await send_help(update)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_stats(update, context)


async def stats_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_stats(update, context)


def get_handlers() -> list:
    return [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("stats", stats_command),
        MessageHandler(BTN_HELP_FILTER, help_command),
        MessageHandler(BTN_STATS_FILTER, stats_button),
        CallbackQueryHandler(start_level_callback, pattern=r"^start:level:"),
        CallbackQueryHandler(start_script_callback, pattern=r"^start:script:"),
        CallbackQueryHandler(help_callback, pattern=r"^menu:help$"),
    ]
