"""Логика викторины и SR-алгоритм."""

from __future__ import annotations

import random
import time
from pathlib import Path

from srblearn import db
from srblearn.models import QuizQuestion, Word, WordProgress
from srblearn.script_prefs import DEFAULT_SCRIPT, display_sr
from srblearn.vocabulary import load_vocabulary

DEFAULT_EASE_FACTOR = 2.5
MIN_EASE_FACTOR = 1.3
EASE_DECREMENT = 0.2
EASE_INCREMENT = 0.1
SECONDS_PER_DAY = 86_400
NEW_WORD_RATIO = 0.7  # 70% новых, 30% повторения
RECENT_WINDOW = 12  # не повторять слово в пределах последних N вопросов сессии
RETRY_DELAY = 4  # после ошибки — минимум столько других слов до повтора

QUIZ_MODE_SR_RU = "sr_ru"
QUIZ_MODE_RU_SR = "ru_sr"
QUIZ_MODES = (QUIZ_MODE_SR_RU, QUIZ_MODE_RU_SR)


def vocab_to_word(entry: dict) -> Word:
    return Word(
        sr=entry["sr"],
        sr_lat=entry.get("sr_lat") or entry["sr"],
        ru=entry["ru"],
        tags=entry["tags"],
    )


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
    script: str = DEFAULT_SCRIPT,
    option_count: int = 4,
) -> QuizQuestion:
    """Собрать вопрос с 4 вариантами ответа (1 правильный + 3 дистрактора)."""
    if mode not in QUIZ_MODES:
        raise ValueError(f"Unknown quiz mode: {mode}")

    if mode == QUIZ_MODE_SR_RU:
        correct_answer = word.ru
        pool = [w.ru for w in vocabulary if w.ru != correct_answer]
        prompt = display_sr(word, script)
    else:
        correct_answer = display_sr(word, script)
        pool = [
            display_sr(w, script)
            for w in vocabulary
            if w.sr != word.sr
        ]
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
        script: str = DEFAULT_SCRIPT,
    ) -> None:
        if mode not in QUIZ_MODES:
            raise ValueError(f"Unknown quiz mode: {mode}")

        self.db_path = db_path
        self.user_id = user_id
        self.level = level
        self.mode = mode
        self.script = script
        self._vocabulary: list[Word] = []
        self._words_by_sr: dict[str, Word] = {}
        self._pick_counter = 0
        self._recent_srs: list[str] = []
        self._retry_pending: list[str] = []

    async def load_vocabulary(self) -> None:
        entries = load_vocabulary(self.level)
        self._vocabulary = [vocab_to_word(entry) for entry in entries]
        self._words_by_sr = {word.sr: word for word in self._vocabulary}

    async def get_next_question(self) -> QuizQuestion | None:
        word = await self._select_word()
        if word is None:
            return None
        self._note_shown(word.sr)
        return build_quiz_question(
            word, self._vocabulary, self.mode, script=self.script
        )

    async def record_answer(self, word_sr: str, is_correct: bool) -> WordProgress:
        now = time.time()
        progress = await db.get_word_progress(
            self.db_path, self.user_id, word_sr, self.level
        )
        if progress is None:
            progress = new_word_progress(self.user_id, word_sr, self.level)

        if is_correct:
            progress = apply_correct(progress, now)
            if word_sr in self._retry_pending:
                self._retry_pending.remove(word_sr)
        else:
            progress = apply_incorrect(progress, now)
            self._schedule_retry(word_sr)

        return await db.upsert_word_progress(self.db_path, progress)

    def _note_shown(self, word_sr: str) -> None:
        if word_sr in self._recent_srs:
            self._recent_srs.remove(word_sr)
        self._recent_srs.append(word_sr)
        if len(self._recent_srs) > RECENT_WINDOW:
            self._recent_srs = self._recent_srs[-RECENT_WINDOW:]

    def _schedule_retry(self, word_sr: str) -> None:
        if word_sr in self._retry_pending:
            self._retry_pending.remove(word_sr)
        self._retry_pending.append(word_sr)

    def _recent_set(self) -> set[str]:
        return set(self._recent_srs)

    def _blocked_for_retry(self) -> set[str]:
        if not self._recent_srs:
            return set()
        return set(self._recent_srs[-RETRY_DELAY:])

    def _eligible_retries(self) -> list[str]:
        recent = self._recent_set()
        blocked = self._blocked_for_retry()
        return [
            sr for sr in self._retry_pending
            if sr not in recent and sr not in blocked
        ]

    def _pick_random_word(self, words: list[Word], *, exclude: set[str]) -> Word | None:
        eligible = [word for word in words if word.sr not in exclude]
        if not eligible:
            return None
        return random.choice(eligible)

    async def _select_word(self) -> Word | None:
        if not self._vocabulary:
            await self.load_vocabulary()

        recent = self._recent_set()
        last_shown = self._recent_srs[-1] if self._recent_srs else None

        retries = self._eligible_retries()
        if retries:
            word_sr = retries[0]
            self._retry_pending.remove(word_sr)
            return self._words_by_sr.get(word_sr)

        now = time.time()
        due = await db.get_due_word_progress(
            self.db_path, self.user_id, self.level, now
        )
        if due:
            due.sort(key=lambda item: (-item.error_count, item.next_review))
            due_words = [
                self._words_by_sr[item.word_sr]
                for item in due
                if item.word_sr in self._words_by_sr
            ]
            picked = self._pick_random_word(due_words, exclude=recent)
            if picked is not None:
                return picked

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
            picked = self._pick_random_word(new_words, exclude=recent)
            if picked is not None:
                return picked
        if review_words:
            picked = self._pick_random_word(review_words, exclude=recent)
            if picked is not None:
                return picked
        if new_words:
            picked = self._pick_random_word(new_words, exclude=recent)
            if picked is not None:
                return picked

        # Ослабляем фильтр: можно повторить, но не слово с предыдущего вопроса
        soft_exclude = {last_shown} if last_shown else set()
        if due:
            due_words = [
                self._words_by_sr[item.word_sr]
                for item in due
                if item.word_sr in self._words_by_sr
            ]
            picked = self._pick_random_word(due_words, exclude=soft_exclude)
            if picked is not None:
                return picked
        if pick_new and new_words:
            picked = self._pick_random_word(new_words, exclude=soft_exclude)
            if picked is not None:
                return picked
        if review_words:
            picked = self._pick_random_word(review_words, exclude=soft_exclude)
            if picked is not None:
                return picked
        if new_words:
            picked = self._pick_random_word(new_words, exclude=soft_exclude)
            if picked is not None:
                return picked

        return None

    def _should_pick_new(self) -> bool:
        """70% новых слов, 30% повторения (когда нет просроченных)."""
        self._pick_counter += 1
        threshold = int(NEW_WORD_RATIO * 10)
        return (self._pick_counter % 10) < threshold
