"""Общие утилиты для хендлеров."""

from __future__ import annotations

import re
from pathlib import Path

from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, filters

from srblearn.config import LEVELS
from srblearn.script_prefs import SCRIPT_CYRILLIC, SCRIPT_LABELS, SCRIPT_LATIN

BTN_QUIZ = "📝 Викторина"
BTN_SETTINGS = "⚙️ Настройки"
BTN_STATS = "📊 Статистика"
BTN_HELP = "❓ Справка"

MENU_BUTTONS = {BTN_QUIZ, BTN_SETTINGS, BTN_STATS, BTN_HELP}

BTN_QUIZ_FILTER = filters.Regex(f"^{re.escape(BTN_QUIZ)}$")
BTN_SETTINGS_FILTER = filters.Regex(f"^{re.escape(BTN_SETTINGS)}$")
BTN_STATS_FILTER = filters.Regex(f"^{re.escape(BTN_STATS)}$")
BTN_HELP_FILTER = filters.Regex(f"^{re.escape(BTN_HELP)}$")


def get_db_path(context: ContextTypes.DEFAULT_TYPE) -> Path:
    return context.application.bot_data["db_path"]


async def refresh_user_notifications(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> None:
    refresh = context.application.bot_data.get("refresh_user_notifications")
    if refresh is not None:
        await refresh(user_id)


def level_keyboard(prefix: str) -> list[list[tuple[str, str]]]:
    """Кнопки уровней: prefix используется в callback_data (например settings:level)."""
    rows: list[list[tuple[str, str]]] = []
    row: list[tuple[str, str]] = []
    for index, level in enumerate(LEVELS):
        row.append((level, f"{prefix}:{level}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def script_keyboard(prefix: str) -> list[list[tuple[str, str]]]:
    return [
        [
            ("🔤 Кириллица", f"{prefix}:{SCRIPT_CYRILLIC}"),
            ("🔤 Latinica", f"{prefix}:{SCRIPT_LATIN}"),
        ],
    ]


def script_keyboard_markup(prefix: str):
    return inline_keyboard(script_keyboard(prefix))


def inline_keyboard(buttons: list[list[tuple[str, str]]]):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text, callback_data=data) for text, data in row]
            for row in buttons
        ]
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Постоянная клавиатура с основными действиями."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_QUIZ), KeyboardButton(BTN_STATS)],
            [KeyboardButton(BTN_SETTINGS), KeyboardButton(BTN_HELP)],
        ],
        resize_keyboard=True,
    )
