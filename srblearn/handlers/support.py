"""Обработчик /support — пожелания и багрепорты."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from srblearn import feedback
from srblearn.handlers.common import (
    BTN_HELP_FILTER,
    BTN_QUIZ_FILTER,
    BTN_SETTINGS_FILTER,
    BTN_STATS_FILTER,
    main_menu_keyboard,
)

AWAITING_MESSAGE = 0

PROMPT_TEXT = (
    "💬 *Поддержка SrbLearn*\n\n"
    "Здесь можно отправить:\n"
    "• сообщение об ошибке (багрепорт)\n"
    "• пожелание или идею\n"
    "• вопрос по работе бота\n\n"
    "Напишите одним сообщением всё, что хотите передать — "
    "мы сохраним его и учтём при доработках.\n\n"
    "Отмена: /cancel"
)

THANK_YOU_TEXT = (
    "✅ Спасибо! Ваше сообщение сохранено.\n"
    "Мы разберём его и постараемся учесть в следующих обновлениях."
)

CANCEL_TEXT = "Обращение отменено."


def get_support_file(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data["config"].support_file


async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    await update.message.reply_text(
        PROMPT_TEXT,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    return AWAITING_MESSAGE


async def support_receive_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    if update.message is None or update.effective_user is None:
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Сообщение пустое. Напишите текст или /cancel.")
        return AWAITING_MESSAGE

    await feedback.save_support_message(
        get_support_file(context),
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        message=text,
    )

    await update.message.reply_text(
        THANK_YOU_TEXT,
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def support_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is not None:
        await update.message.reply_text(CANCEL_TEXT, reply_markup=main_menu_keyboard())
    return ConversationHandler.END


def get_handlers() -> list:
    conversation = ConversationHandler(
        entry_points=[CommandHandler("support", support_start)],
        states={
            AWAITING_MESSAGE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND
                    & ~BTN_QUIZ_FILTER
                    & ~BTN_SETTINGS_FILTER
                    & ~BTN_STATS_FILTER
                    & ~BTN_HELP_FILTER,
                    support_receive_message,
                ),
            ],
        },
        fallbacks=[CommandHandler("cancel", support_cancel)],
        allow_reentry=True,
    )
    return [conversation]
