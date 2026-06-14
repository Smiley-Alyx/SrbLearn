"""Общие утилиты для хендлеров."""

from __future__ import annotations

from pathlib import Path

from telegram.ext import ContextTypes

from srblearn.config import LEVELS


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


def inline_keyboard(buttons: list[list[tuple[str, str]]]):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text, callback_data=data) for text, data in row]
            for row in buttons
        ]
    )
