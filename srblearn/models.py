"""Dataclasses: Word, UserProgress, UserSettings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Word:
    sr: str
    ru: str
    tags: list[str]


@dataclass
class User:
    user_id: int
    username: str | None
    level: str
    notifications_enabled: bool
    notify_times: list[str]
    notify_count: int
    created_at: float


@dataclass
class WordProgress:
    id: int
    user_id: int
    word_sr: str
    level: str
    ease_factor: float
    interval_days: float
    next_review: float
    error_count: int
    correct_count: int
    last_seen: float | None


@dataclass
class Session:
    id: int
    user_id: int
    started_at: float
    ended_at: float | None
    correct: int
    total: int
    mode: str


@dataclass
class UserStats:
    words_learned: int
    total_answers: int
    correct_answers: int
    accuracy: float
    words_due: int
