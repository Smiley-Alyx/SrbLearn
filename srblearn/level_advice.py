"""Рекомендации по переходу на следующий уровень."""

from __future__ import annotations

from srblearn.config import LEVELS
from srblearn.models import UserStats

LEVEL_UP_COVERAGE = 0.65
LEVEL_UP_ACCURACY = 78.0
LEVEL_UP_MIN_ANSWERS = 40
MAX_DUE_RATIO = 0.25
ALMOST_COVERAGE = 0.45
ALMOST_ACCURACY = 70.0


def _next_level(level: str) -> str | None:
    try:
        index = LEVELS.index(level.upper())
    except ValueError:
        return None
    if index + 1 >= len(LEVELS):
        return None
    return LEVELS[index + 1]


def get_level_recommendation(
    level: str,
    stats: UserStats,
    vocab_size: int,
) -> str:
    level = level.upper()
    next_level = _next_level(level)

    if vocab_size <= 0:
        return "💡 *Рекомендация:* данных для оценки пока недостаточно."

    if next_level is None:
        return (
            "🏆 *Рекомендация:* вы на максимальном уровне *C2*. "
            "Продолжайте повторять и закреплять лексику."
        )

    coverage = stats.words_learned / vocab_size
    due_ratio = stats.words_due / stats.words_learned if stats.words_learned else 0.0

    if stats.words_learned and due_ratio > MAX_DUE_RATIO:
        return (
            f"⏳ *Рекомендация:* пока оставайтесь на *{level}*. "
            f"Сначала разберите слова на повторении ({stats.words_due} шт.) — "
            f"это больше {int(MAX_DUE_RATIO * 100)}% изученных."
        )

    ready = (
        coverage >= LEVEL_UP_COVERAGE
        and stats.accuracy >= LEVEL_UP_ACCURACY
        and stats.total_answers >= LEVEL_UP_MIN_ANSWERS
    )
    if ready:
        return (
            f"✅ *Рекомендация:* можно переходить на *{next_level}*! "
            f"Освоено {stats.words_learned} из {vocab_size} слов "
            f"({coverage * 100:.0f}%), точность {stats.accuracy:.1f}%."
        )

    missing: list[str] = []
    if coverage < LEVEL_UP_COVERAGE:
        need_words = int(LEVEL_UP_COVERAGE * vocab_size) - stats.words_learned
        missing.append(f"ещё ~{max(need_words, 1)} слов")
    if stats.accuracy < LEVEL_UP_ACCURACY:
        missing.append(f"точность от {LEVEL_UP_ACCURACY:.0f}% (сейчас {stats.accuracy:.1f}%)")
    if stats.total_answers < LEVEL_UP_MIN_ANSWERS:
        missing.append(
            f"больше практики (от {LEVEL_UP_MIN_ANSWERS} ответов, сейчас {stats.total_answers})"
        )
    hints = ", ".join(missing)

    almost = coverage >= ALMOST_COVERAGE or stats.accuracy >= ALMOST_ACCURACY
    if almost and stats.total_answers >= 20:
        return (
            f"📈 *Рекомендация:* почти готовы к *{next_level}*, но пока оставайтесь на *{level}*. "
            f"Нужно: {hints}."
        )

    return (
        f"📚 *Рекомендация:* пока оставайтесь на *{level}*. "
        f"Прогресс: {stats.words_learned}/{vocab_size} слов ({coverage * 100:.0f}%). "
        f"Цель для перехода: {hints}."
    )
