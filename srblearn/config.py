"""Загрузка конфигурации из .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = "progress.db"
DEFAULT_SUPPORT_FILE = "support_messages.jsonl"
DEFAULT_LEVEL = "A1"
LEVELS: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")


@dataclass(frozen=True)
class Config:
    bot_token: str
    db_path: Path
    support_file: Path


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN is not set in environment")

    db_path = Path(os.getenv("DB_PATH", DEFAULT_DB_PATH))
    support_file = Path(os.getenv("SUPPORT_FILE", DEFAULT_SUPPORT_FILE))
    return Config(bot_token=bot_token, db_path=db_path, support_file=support_file)
