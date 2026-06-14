"""Загрузчик словарей по уровню."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

LEVELS: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

_VOCAB_DIR = Path(__file__).parent
_cache: dict[str, list[VocabularyEntry]] = {}


class VocabularyEntry(TypedDict):
    sr: str
    ru: str
    tags: list[str]


def load_vocabulary(level: str) -> list[VocabularyEntry]:
    """Загрузить словарь для уровня (A1–C2). Результат кэшируется."""
    level = level.upper()
    if level not in LEVELS:
        raise ValueError(f"Unknown level: {level}")

    if level not in _cache:
        path = _VOCAB_DIR / f"{level.lower()}.json"
        with path.open(encoding="utf-8") as f:
            _cache[level] = json.load(f)

    return _cache[level]


def word_count(level: str) -> int:
    """Количество слов в словаре уровня."""
    return len(load_vocabulary(level))


def clear_cache() -> None:
    """Сбросить кэш (для тестов)."""
    _cache.clear()
