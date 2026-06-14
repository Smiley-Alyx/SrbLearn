"""Тесты quiz_engine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from srblearn import db, quiz_engine
from srblearn.models import Word, WordProgress


@pytest.fixture
async def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    await db.init_db(path)
    await db.create_user(path, 1, level="A1")
    return path


def test_apply_correct_first_answer() -> None:
    progress = quiz_engine.new_word_progress(1, "здраво", "A1")
    updated = quiz_engine.apply_correct(progress, now=1000)

    assert updated.correct_count == 1
    assert updated.interval_days == 1
    assert updated.ease_factor == 2.6
    assert updated.next_review == 1000 + quiz_engine.SECONDS_PER_DAY


def test_apply_correct_scales_interval() -> None:
    progress = quiz_engine.new_word_progress(1, "здраво", "A1")
    progress.interval_days = 2
    progress.ease_factor = 2.5

    updated = quiz_engine.apply_correct(progress, now=0)
    assert updated.interval_days == 5
    assert updated.ease_factor == 2.6


def test_apply_incorrect_resets_interval() -> None:
    progress = quiz_engine.new_word_progress(1, "здраво", "A1")
    progress.interval_days = 10
    progress.ease_factor = 2.7

    updated = quiz_engine.apply_incorrect(progress, now=500)
    assert updated.error_count == 1
    assert updated.interval_days == 1
    assert updated.ease_factor == 2.5
    assert updated.next_review == 500 + quiz_engine.SECONDS_PER_DAY


def test_apply_incorrect_respects_min_ease_factor() -> None:
    progress = quiz_engine.new_word_progress(1, "здраво", "A1")
    progress.ease_factor = 1.4

    updated = quiz_engine.apply_incorrect(progress)
    assert updated.ease_factor == quiz_engine.MIN_EASE_FACTOR


def test_build_quiz_question_sr_ru() -> None:
    vocabulary = [
        Word("а", "a", "один", []),
        Word("б", "b", "два", []),
        Word("в", "v", "три", []),
        Word("г", "g", "четыре", []),
    ]
    with patch("srblearn.quiz_engine.random.shuffle", side_effect=lambda x: None):
        question = quiz_engine.build_quiz_question(vocabulary[0], vocabulary, "sr_ru")

    assert question.prompt == "а"
    assert question.options[question.correct_index] == "один"
    assert len(question.options) == 4
    assert len(set(question.options)) == 4


def test_build_quiz_question_ru_sr() -> None:
    vocabulary = [
        Word("а", "a", "один", []),
        Word("б", "b", "два", []),
        Word("в", "v", "три", []),
        Word("г", "g", "четыре", []),
    ]
    with patch("srblearn.quiz_engine.random.shuffle", side_effect=lambda x: None):
        question = quiz_engine.build_quiz_question(vocabulary[0], vocabulary, "ru_sr")

    assert question.prompt == "один"
    assert question.options[question.correct_index] == "а"


def test_build_quiz_question_latin_script() -> None:
    vocabulary = [
        Word("здраво", "zdravo", "привет", []),
        Word("хвала", "hvala", "спасибо", []),
        Word("да", "da", "да", []),
        Word("не", "ne", "нет", []),
    ]
    with patch("srblearn.quiz_engine.random.shuffle", side_effect=lambda x: None):
        question = quiz_engine.build_quiz_question(
            vocabulary[0], vocabulary, "ru_sr", script="latin"
        )

    assert question.prompt == "привет"
    assert question.options[question.correct_index] == "zdravo"


def test_should_pick_new_ratio() -> None:
    session = quiz_engine.QuizSession(Path("unused.db"), 1, "A1", "sr_ru")
    picks = [session._should_pick_new() for _ in range(10)]
    assert picks.count(True) == 7
    assert picks.count(False) == 3


@pytest.mark.asyncio
async def test_quiz_session_record_answer_persists(db_path: Path) -> None:
    session = quiz_engine.QuizSession(db_path, 1, "A1", "sr_ru")
    saved = await session.record_answer("здраво", is_correct=True)

    assert saved.correct_count == 1
    stored = await db.get_word_progress(db_path, 1, "здраво", "A1")
    assert stored is not None
    assert stored.correct_count == 1


@pytest.mark.asyncio
async def test_wrong_answer_not_immediate_repeat(db_path: Path) -> None:
    session = quiz_engine.QuizSession(db_path, 1, "A1", "sr_ru")
    session._vocabulary = [
        Word("здраво", "zdravo", "привет", []),
        Word("хвала", "hvala", "спасибо", []),
        Word("да", "da", "да", []),
    ]
    session._words_by_sr = {word.sr: word for word in session._vocabulary}

    session._note_shown("здраво")
    await session.record_answer("здраво", is_correct=False)
    next_word = await session._select_word()

    assert next_word is not None
    assert next_word.sr != "здраво"


@pytest.mark.asyncio
async def test_recent_window_avoids_immediate_repeat(db_path: Path) -> None:
    session = quiz_engine.QuizSession(db_path, 1, "A1", "sr_ru")
    words = [Word(f"слово{i}", f"slovo{i}", f"ru{i}", []) for i in range(6)]
    session._vocabulary = words
    session._words_by_sr = {word.sr: word for word in words}
    session._recent_srs = ["слово0"]

    picked = session._pick_random_word(words, exclude=session._recent_set())
    assert picked is not None
    assert picked.sr != "слово0"


@pytest.mark.asyncio
async def test_deferred_retry_after_other_words(db_path: Path) -> None:
    session = quiz_engine.QuizSession(db_path, 1, "A1", "sr_ru")
    session._vocabulary = [
        Word("здраво", "zdravo", "привет", []),
        Word("хвала", "hvala", "спасибо", []),
    ]
    session._words_by_sr = {word.sr: word for word in session._vocabulary}

    await session.record_answer("здраво", is_correct=False)
    session._note_shown("хвала")
    session._note_shown("да")
    session._note_shown("не")
    session._note_shown("може")

    retries = session._eligible_retries()
    assert "здраво" in retries


@pytest.mark.asyncio
async def test_quiz_session_prefers_due_words(db_path: Path) -> None:
    await db.upsert_word_progress(
        db_path,
        WordProgress(
            id=0,
            user_id=1,
            word_sr="здраво",
            level="A1",
            ease_factor=2.5,
            interval_days=1,
            next_review=10,
            error_count=0,
            correct_count=1,
            last_seen=5,
        ),
    )
    await db.upsert_word_progress(
        db_path,
        WordProgress(
            id=0,
            user_id=1,
            word_sr="довиђења",
            level="A1",
            ease_factor=2.5,
            interval_days=5,
            next_review=1000,
            error_count=0,
            correct_count=1,
            last_seen=5,
        ),
    )

    session = quiz_engine.QuizSession(db_path, 1, "A1", "sr_ru")
    session._vocabulary = [
        Word("здраво", "zdravo", "привет", []),
        Word("довиђења", "doviđenja", "до свидания", []),
    ]
    session._words_by_sr = {word.sr: word for word in session._vocabulary}

    with patch("srblearn.quiz_engine.time.time", return_value=100):
        selected = await session._select_word()

    assert selected is not None
    assert selected.sr == "здраво"
