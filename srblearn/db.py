"""SQLite: инициализация и CRUD."""

from __future__ import annotations

import json
import time
from pathlib import Path

import aiosqlite

from srblearn.config import DEFAULT_LEVEL
from srblearn.models import Session, User, UserStats, WordProgress

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    level TEXT NOT NULL DEFAULT 'A1',
    notifications_enabled INTEGER NOT NULL DEFAULT 0,
    notify_times TEXT NOT NULL DEFAULT '[]',
    notify_count INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS word_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    word_sr TEXT NOT NULL,
    level TEXT NOT NULL,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    interval_days REAL NOT NULL DEFAULT 0,
    next_review REAL NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    last_seen REAL,
    UNIQUE(user_id, word_sr, level),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    started_at REAL NOT NULL,
    ended_at REAL,
    correct INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL DEFAULT 0,
    mode TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_word_progress_user_level
    ON word_progress(user_id, level);
CREATE INDEX IF NOT EXISTS idx_word_progress_next_review
    ON word_progress(user_id, next_review);
"""


def _row_to_user(row: aiosqlite.Row) -> User:
    return User(
        user_id=row["user_id"],
        username=row["username"],
        level=row["level"],
        notifications_enabled=bool(row["notifications_enabled"]),
        notify_times=json.loads(row["notify_times"]),
        notify_count=row["notify_count"],
        created_at=row["created_at"],
    )


def _row_to_word_progress(row: aiosqlite.Row) -> WordProgress:
    return WordProgress(
        id=row["id"],
        user_id=row["user_id"],
        word_sr=row["word_sr"],
        level=row["level"],
        ease_factor=row["ease_factor"],
        interval_days=row["interval_days"],
        next_review=row["next_review"],
        error_count=row["error_count"],
        correct_count=row["correct_count"],
        last_seen=row["last_seen"],
    )


def _row_to_session(row: aiosqlite.Row) -> Session:
    return Session(
        id=row["id"],
        user_id=row["user_id"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        correct=row["correct"],
        total=row["total"],
        mode=row["mode"],
    )


async def init_db(db_path: Path) -> None:
    """Создать таблицы, если их ещё нет."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript(_SCHEMA)
        await db.commit()


async def get_user(db_path: Path, user_id: int) -> User | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return _row_to_user(row) if row else None


async def create_user(
    db_path: Path,
    user_id: int,
    username: str | None = None,
    level: str = DEFAULT_LEVEL,
) -> User:
    now = time.time()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO users (user_id, username, level, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, username, level, now),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return _row_to_user(row)


async def get_or_create_user(
    db_path: Path,
    user_id: int,
    username: str | None = None,
) -> User:
    user = await get_user(db_path, user_id)
    if user is not None:
        return user
    return await create_user(db_path, user_id, username)


async def update_user_level(db_path: Path, user_id: int, level: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE users SET level = ? WHERE user_id = ?",
            (level, user_id),
        )
        await db.commit()


async def update_user_notifications(
    db_path: Path,
    user_id: int,
    *,
    enabled: bool,
    notify_count: int,
    notify_times: list[str],
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE users
            SET notifications_enabled = ?,
                notify_count = ?,
                notify_times = ?
            WHERE user_id = ?
            """,
            (
                int(enabled),
                notify_count,
                json.dumps(notify_times, ensure_ascii=False),
                user_id,
            ),
        )
        await db.commit()


async def get_users_with_notifications(db_path: Path) -> list[User]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM users
            WHERE notifications_enabled = 1 AND notify_count > 0
            """
        )
        rows = await cursor.fetchall()
        return [_row_to_user(row) for row in rows]


async def get_word_progress(
    db_path: Path,
    user_id: int,
    word_sr: str,
    level: str,
) -> WordProgress | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM word_progress
            WHERE user_id = ? AND word_sr = ? AND level = ?
            """,
            (user_id, word_sr, level),
        )
        row = await cursor.fetchone()
        return _row_to_word_progress(row) if row else None


async def upsert_word_progress(
    db_path: Path,
    progress: WordProgress,
) -> WordProgress:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        if progress.id:
            await db.execute(
                """
                UPDATE word_progress
                SET ease_factor = ?,
                    interval_days = ?,
                    next_review = ?,
                    error_count = ?,
                    correct_count = ?,
                    last_seen = ?
                WHERE id = ?
                """,
                (
                    progress.ease_factor,
                    progress.interval_days,
                    progress.next_review,
                    progress.error_count,
                    progress.correct_count,
                    progress.last_seen,
                    progress.id,
                ),
            )
            progress_id = progress.id
        else:
            cursor = await db.execute(
                """
                INSERT INTO word_progress (
                    user_id, word_sr, level,
                    ease_factor, interval_days, next_review,
                    error_count, correct_count, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    progress.user_id,
                    progress.word_sr,
                    progress.level,
                    progress.ease_factor,
                    progress.interval_days,
                    progress.next_review,
                    progress.error_count,
                    progress.correct_count,
                    progress.last_seen,
                ),
            )
            progress_id = cursor.lastrowid
        await db.commit()

    result = await get_word_progress_by_id(db_path, progress_id)
    assert result is not None
    return result


async def get_word_progress_by_id(
    db_path: Path,
    progress_id: int,
) -> WordProgress | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM word_progress WHERE id = ?",
            (progress_id,),
        )
        row = await cursor.fetchone()
        return _row_to_word_progress(row) if row else None


async def get_user_word_progress(
    db_path: Path,
    user_id: int,
    level: str,
) -> list[WordProgress]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM word_progress
            WHERE user_id = ? AND level = ?
            ORDER BY next_review ASC
            """,
            (user_id, level),
        )
        rows = await cursor.fetchall()
        return [_row_to_word_progress(row) for row in rows]


async def get_due_word_progress(
    db_path: Path,
    user_id: int,
    level: str,
    now: float | None = None,
) -> list[WordProgress]:
    if now is None:
        now = time.time()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM word_progress
            WHERE user_id = ? AND level = ? AND next_review <= ?
            ORDER BY next_review ASC
            """,
            (user_id, level, now),
        )
        rows = await cursor.fetchall()
        return [_row_to_word_progress(row) for row in rows]


async def get_seen_word_srs(
    db_path: Path,
    user_id: int,
    level: str,
) -> set[str]:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            SELECT word_sr FROM word_progress
            WHERE user_id = ? AND level = ?
            """,
            (user_id, level),
        )
        rows = await cursor.fetchall()
        return {row[0] for row in rows}


async def create_session(
    db_path: Path,
    user_id: int,
    mode: str,
) -> Session:
    now = time.time()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            INSERT INTO sessions (user_id, started_at, mode)
            VALUES (?, ?, ?)
            """,
            (user_id, now, mode),
        )
        session_id = cursor.lastrowid
        await db.commit()
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        return _row_to_session(row)


async def update_session(
    db_path: Path,
    session_id: int,
    *,
    correct: int,
    total: int,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE sessions SET correct = ?, total = ? WHERE id = ?
            """,
            (correct, total, session_id),
        )
        await db.commit()


async def end_session(db_path: Path, session_id: int) -> None:
    now = time.time()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (now, session_id),
        )
        await db.commit()


async def get_user_stats(
    db_path: Path,
    user_id: int,
    level: str,
    now: float | None = None,
) -> UserStats:
    if now is None:
        now = time.time()

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            SELECT
                COUNT(*) AS words_learned,
                COALESCE(SUM(correct_count + error_count), 0) AS total_answers,
                COALESCE(SUM(correct_count), 0) AS correct_answers
            FROM word_progress
            WHERE user_id = ? AND level = ?
            """,
            (user_id, level),
        )
        row = await cursor.fetchone()
        words_learned = row[0]
        total_answers = row[1]
        correct_answers = row[2]

        cursor = await db.execute(
            """
            SELECT COUNT(*) FROM word_progress
            WHERE user_id = ? AND level = ? AND next_review <= ?
            """,
            (user_id, level, now),
        )
        due_row = await cursor.fetchone()
        words_due = due_row[0]

    accuracy = (correct_answers / total_answers * 100) if total_answers else 0.0
    return UserStats(
        words_learned=words_learned,
        total_answers=total_answers,
        correct_answers=correct_answers,
        accuracy=accuracy,
        words_due=words_due,
    )
