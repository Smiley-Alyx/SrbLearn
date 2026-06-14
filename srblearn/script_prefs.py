"""Настройки алфавита для отображения сербских слов."""

from __future__ import annotations

from srblearn.models import Word

SCRIPT_CYRILLIC = "cyrillic"
SCRIPT_LATIN = "latin"
SCRIPTS = (SCRIPT_CYRILLIC, SCRIPT_LATIN)
DEFAULT_SCRIPT = SCRIPT_CYRILLIC

SCRIPT_LABELS = {
    SCRIPT_CYRILLIC: "кириллица",
    SCRIPT_LATIN: "латиница",
}


def display_sr(word: Word, script: str) -> str:
    if script == SCRIPT_LATIN:
        return word.sr_lat
    return word.sr


def script_label(script: str) -> str:
    return SCRIPT_LABELS.get(script, script)
