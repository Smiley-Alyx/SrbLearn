"""Логика викторины и SR-алгоритм."""

from __future__ import annotations

import random
import time
from pathlib import Path

from srblearn import db
from srblearn.models import QuizQuestion, Word, WordProgress
from srblearn.vocabulary import load_vocabulary

DEFAULT_EASE_FACTOR = 2.5
MIN_EASE_FACTOR = 1.3
EASE_DECREMENT = 0.2
EASE_INCREMENT = 0.1
SECONDS_PER_DAY = 86_400
NEW_WORD_RATIO = 0.7  # 70% новых, 30% повторения

QUIZ_MODE_SR_RU = "sr_ru"
QUIZ_MODE_RU_SR = "ru_sr"
QUIZ_MODES = (QUIZ_MODE_SR_RU, QUIZ_MODE_RU_SR)


def vocab_to_word(entry: dict) -> Word:
    return Word(sr=entry["sr"], ru=entry["ru"], tags=entry["tags"])


def new_word_progress(user_id: int, word_sr: str, level: str) -> WordProgress:
    return WordProgress(
        id=0,
        user_id=user_id,
        word_sr=word_sr,
        level=level,
        ease_factor=DEFAULT_EASE_FACTOR,
        interval_days=0,
        next_review=0,
        error_count=0,
        correct_count=0,
        last_seen=None,
    )


def apply_correct(progress: WordProgress, now: float | None = None) -> WordProgress:
    """Обновить прогресс после правильного ответа."""
    if now is None:
        now = time.time()

    progress.correct_count += 1
    if progress.interval_days <= 0:
        progress.interval_days = 1
    else:
        progress.interval_days *= progress.ease_factor

    progress.ease_factor += EASE_INCREMENT
    progress.next_review = now + progress.interval_days * SECONDS_PER_DAY
    progress.last_seen = now
    return progress


def apply_incorrect(progress: WordProgress, now: float | None = None) -> WordProgress:
    """Обновить прогресс после ошибки."""
    if now is None:
        now = time.time()

    progress.error_count += 1
    progress.interval_days = 1
    progress.ease_factor = max(MIN_EASE_FACTOR, progress.ease_factor - EASE_DECREMENT)
    progress.next_review = now + SECONDS_PER_DAY
    progress.last_seen = now
    return progress


def build_quiz_question(
    word: Word,
    vocabulary: list[Word],
    mode: str,
    *,
    option_count: int = 4,
) -> QuizQuestion:
    """Собрать вопрос с 4 вариантами ответа (1 правильный + 3 дистрактора)."""
    if mode not in QUIZ_MODES:
        raise ValueError(f"Unknown quiz mode: {mode}")

    if mode == QUIZ_MODE_SR_RU:
        correct_answer = word.ru
        pool = [w.ru for w in vocabulary if w.ru != correct_answer]
        prompt = word.sr
    else:
        correct_answer = word.sr
        pool = [w.sr for w in vocabulary if w.sr != correct_answer]
        prompt = word.ru

    distractor_count = option_count - 1
    if len(pool) < distractor_count:
        raise ValueError("Not enough words in vocabulary to build distractors")

    distractors = random.sample(pool, distractor_count)
    options = distractors + [correct_answer]
    random.shuffle(options)
    correct_index = options.index(correct_answer)

    return QuizQuestion(
        word=word,
        prompt=prompt,
        options=options,
        correct_index=correct_index,
        mode=mode,
    )


class QuizSession:
    """Сессия викторины: выборка слов и обновление прогресса."""

    def __init__(
        self,
        db_path: Path,
        user_id: int,
        level: str,
        mode: str,
    ) -> None:
        if mode not in QUIZ_MODES:
            raise ValueError(f"Unknown quiz mode: {mode}")

        self.db_path = db_path
        self.user_id = user_id
        self.level = level
        self.mode = mode
        self._vocabulary: list[Word] = []
        self._words_by_sr: dict[str, Word] = {}
        self._pick_counter = 0
        self._priority_queue: list[str] = []

    async def load_vocabulary(self) -> None:
        entries = load_vocabulary(self.level)
        self._vocabulary = [vocab_to_word(entry) for entry in entries]
        self._words_by_sr = {word.sr: word for word in self._vocabulary}

    async def get_next_question(self) -> QuizQuestion | None:
        word = await self._select_word()
        if word is None:
            return None
        return build_quiz_question(word, self._vocabulary, self.mode)

    async def record_answer(self, word_sr: str, is_correct: bool) -> WordProgress:
        now = time.time()
        progress = await db.get_word_progress(
            self.db_path, self.user_id, word_sr, self.level
        )
        if progress is None:
            progress = new_word_progress(self.user_id, word_sr, self.level)

        if is_correct:
            progress = apply_correct(progress, now)
        else:
            progress = apply_incorrect(progress, now)
            self._add_to_priority_queue(word_sr)

        return await db.upsert_word_progress(self.db_path, progress)

    def _add_to_priority_queue(self, word_sr: str) -> None:
        if word_sr in self._priority_queue:
            self._priority_queue.remove(word_sr)
        self._priority_queue.insert(0, word_sr)

    async def _select_word(self) -> Word | None:
        if not self._vocabulary:
            await self.load_vocabulary()

        if self._priority_queue:
            word_sr = self._priority_queue.pop(0)
            return self._words_by_sr.get(word_sr)

        now = time.time()
        due = await db.get_due_word_progress(
            self.db_path, self.user_id, self.level, now
        )
        if due:
            due.sort(key=lambda item: (-item.error_count, item.next_review))
            return self._words_by_sr[due[0].word_sr]

        seen = await db.get_seen_word_srs(self.db_path, self.user_id, self.level)
        new_words = [word for word in self._vocabulary if word.sr not in seen]
        in_progress = await db.get_user_word_progress(
            self.db_path, self.user_id, self.level
        )
        review_words = [
            self._words_by_sr[item.word_sr]
            for item in in_progress
            if item.word_sr in self._words_by_sr
        ]

        pick_new = self._should_pick_new()

        if pick_new and new_words:
            return random.choice(new_words)
        if review_words:
            return random.choice(review_words)
        if new_words:
            return random.choice(new_words)

        return None

    def _should_pick_new(self) -> bool:
        """70% новых слов, 30% повторения (когда нет просроченных)."""
        self._pick_counter += 1
        threshold = int(NEW_WORD_RATIO * 10)
        return (self._pick_counter % 10) < threshold
