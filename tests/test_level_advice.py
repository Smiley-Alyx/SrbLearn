"""Тесты level_advice."""

from __future__ import annotations

from srblearn.level_advice import get_level_recommendation
from srblearn.models import UserStats


def _stats(
    *,
    words_learned: int = 0,
    total_answers: int = 0,
    correct_answers: int = 0,
    words_due: int = 0,
) -> UserStats:
    accuracy = (correct_answers / total_answers * 100) if total_answers else 0.0
    return UserStats(
        words_learned=words_learned,
        total_answers=total_answers,
        correct_answers=correct_answers,
        accuracy=accuracy,
        words_due=words_due,
    )


def test_recommends_stay_for_beginner() -> None:
    text = get_level_recommendation("A1", _stats(), vocab_size=300)
    assert "оставайтесь на *A1*" in text


def test_recommends_level_up_when_ready() -> None:
    stats = _stats(
        words_learned=240,
        total_answers=120,
        correct_answers=100,
        words_due=10,
    )
    text = get_level_recommendation("A1", stats, vocab_size=300)
    assert "можно переходить на *A2*" in text


def test_recommends_review_first_when_many_due() -> None:
    stats = _stats(
        words_learned=100,
        total_answers=80,
        correct_answers=70,
        words_due=40,
    )
    text = get_level_recommendation("A1", stats, vocab_size=300)
    assert "повторении" in text
    assert "A2" not in text


def test_max_level_message() -> None:
    stats = _stats(words_learned=200, total_answers=100, correct_answers=90)
    text = get_level_recommendation("C2", stats, vocab_size=500)
    assert "максимальном уровне *C2*" in text


def test_almost_ready_message() -> None:
    stats = _stats(
        words_learned=150,
        total_answers=50,
        correct_answers=40,
        words_due=5,
    )
    text = get_level_recommendation("A1", stats, vocab_size=300)
    assert "почти готовы" in text
