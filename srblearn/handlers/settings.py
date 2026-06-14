"""Обработчик /settings — FSM настроек."""

from __future__ import annotations

import re

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from srblearn import db
from srblearn.handlers.common import (
    get_db_path,
    inline_keyboard,
    level_keyboard,
    refresh_user_notifications,
)

CHOOSING_LEVEL, CHOOSING_NOTIFICATIONS, CHOOSING_FREQUENCY, ENTERING_TIME = range(4)

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

CANCEL_TEXT = "Настройка отменена. Текущие настройки не изменены."


def _reset_settings_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        "settings_level",
        "settings_notifications",
        "settings_notify_count",
        "settings_notify_times",
        "settings_time_index",
    ):
        context.user_data.pop(key, None)


async def settings_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    if update.effective_user is None or update.message is None:
        return ConversationHandler.END

    _reset_settings_data(context)
    db_path = get_db_path(context)
    user = await db.get_or_create_user(
        db_path,
        update.effective_user.id,
        update.effective_user.username,
    )

    context.user_data["settings_level"] = user.level
    context.user_data["settings_notifications"] = user.notifications_enabled
    context.user_data["settings_notify_count"] = user.notify_count
    context.user_data["settings_notify_times"] = list(user.notify_times)

    keyboard = inline_keyboard(level_keyboard("settings:level"))
    await update.message.reply_text(
        "⚙️ *Настройки*\n\nШаг 1/4 — выберите уровень:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    return CHOOSING_LEVEL


async def settings_choose_level(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    query = update.callback_query
    if query is None or query.data is None:
        return ConversationHandler.END

    await query.answer()
    level = query.data.split(":")[-1]
    context.user_data["settings_level"] = level

    keyboard = inline_keyboard(
        [
            [("✅ Включить", "settings:notif:yes"), ("❌ Выключить", "settings:notif:no")],
        ]
    )
    await query.edit_message_text(
        f"Уровень: *{level}*\n\nШаг 2/4 — уведомления:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    return CHOOSING_NOTIFICATIONS


async def settings_choose_notifications(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    query = update.callback_query
    if query is None or query.data is None or update.effective_user is None:
        return ConversationHandler.END

    await query.answer()
    enabled = query.data.endswith(":yes")
    context.user_data["settings_notifications"] = enabled

    if not enabled:
        return await _save_settings(update, context, query.message)

    keyboard = inline_keyboard(
        [
            [
                ("1 раз", "settings:freq:1"),
                ("2 раза", "settings:freq:2"),
                ("3 раза", "settings:freq:3"),
            ],
        ]
    )
    await query.edit_message_text(
        "Шаг 3/4 — сколько раз в сутки напоминать?",
        reply_markup=keyboard,
    )
    return CHOOSING_FREQUENCY


async def settings_choose_frequency(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    query = update.callback_query
    if query is None or query.data is None:
        return ConversationHandler.END

    await query.answer()
    notify_count = int(query.data.split(":")[-1])
    context.user_data["settings_notify_count"] = notify_count
    context.user_data["settings_notify_times"] = []
    context.user_data["settings_time_index"] = 0

    await query.edit_message_text(
        f"Шаг 4/4 — введите время для слота 1 из {notify_count} (формат HH:MM):"
    )
    return ENTERING_TIME


async def settings_enter_time(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    if update.message is None or update.effective_user is None:
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    if not TIME_PATTERN.match(text):
        await update.message.reply_text(
            "Неверный формат. Введите время как HH:MM (например 09:30):"
        )
        return ENTERING_TIME

    times: list[str] = context.user_data.setdefault("settings_notify_times", [])
    times.append(text)

    notify_count: int = context.user_data["settings_notify_count"]
    if len(times) < notify_count:
        slot = len(times) + 1
        await update.message.reply_text(
            f"Введите время для слота {slot} из {notify_count} (HH:MM):"
        )
        return ENTERING_TIME

    return await _save_settings(update, context)


async def _save_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message=None,
) -> int:
    if update.effective_user is None:
        return ConversationHandler.END

    db_path = get_db_path(context)
    user_id = update.effective_user.id

    level = context.user_data.get("settings_level", "A1")
    enabled = context.user_data.get("settings_notifications", False)
    notify_count = context.user_data.get("settings_notify_count", 1)
    notify_times = context.user_data.get("settings_notify_times", [])

    await db.update_user_level(db_path, user_id, level)
    await db.update_user_notifications(
        db_path,
        user_id,
        enabled=enabled,
        notify_count=notify_count if enabled else 0,
        notify_times=notify_times if enabled else [],
    )
    await refresh_user_notifications(context, user_id)

    if enabled:
        times_text = ", ".join(notify_times)
        summary = (
            f"✅ Настройки сохранены!\n\n"
            f"Уровень: {level}\n"
            f"Уведомления: включены ({notify_count}×/сутки)\n"
            f"Время: {times_text}"
        )
    else:
        summary = (
            f"✅ Настройки сохранены!\n\n"
            f"Уровень: {level}\n"
            f"Уведомления: выключены"
        )

    if message is not None:
        await message.edit_text(summary)
    elif update.message is not None:
        await update.message.reply_text(summary)

    _reset_settings_data(context)
    return ConversationHandler.END


async def settings_cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    _reset_settings_data(context)
    if update.message is not None:
        await update.message.reply_text(CANCEL_TEXT)
    return ConversationHandler.END


def get_handlers() -> list:
    conversation = ConversationHandler(
        entry_points=[CommandHandler("settings", settings_start)],
        states={
            CHOOSING_LEVEL: [
                CallbackQueryHandler(settings_choose_level, pattern=r"^settings:level:"),
            ],
            CHOOSING_NOTIFICATIONS: [
                CallbackQueryHandler(
                    settings_choose_notifications,
                    pattern=r"^settings:notif:",
                ),
            ],
            CHOOSING_FREQUENCY: [
                CallbackQueryHandler(
                    settings_choose_frequency,
                    pattern=r"^settings:freq:",
                ),
            ],
            ENTERING_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_enter_time),
            ],
        },
        fallbacks=[CommandHandler("cancel", settings_cancel)],
        allow_reentry=True,
    )
    return [conversation]
