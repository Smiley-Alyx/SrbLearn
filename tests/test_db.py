"""Тесты db."""

from __future__ import annotations

from pathlib import Path

import pytest

from srblearn import db
from srblearn.models import WordProgress

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    await db.init_db(path)
    return path


async def test_init_db_is_idempotent(db_path: Path) -> None:
    await db.init_db(db_path)
    user = await db.create_user(db_path, 1)
    assert user.user_id == 1


async def test_create_and_get_user(db_path: Path) -> None:
    created = await db.create_user(db_path, 42, "alice", "B1")
    assert created.username == "alice"
    assert created.level == "B1"
    assert created.notifications_enabled is False

    fetched = await db.get_user(db_path, 42)
    assert fetched is not None
    assert fetched.username == "alice"


async def test_get_or_create_user(db_path: Path) -> None:
    first = await db.get_or_create_user(db_path, 7, "bob")
    second = await db.get_or_create_user(db_path, 7, "bob2")
    assert first.user_id == second.user_id
    assert second.username == "bob"


async def test_update_user_level(db_path: Path) -> None:
    await db.create_user(db_path, 1, level="A1")
    await db.update_user_level(db_path, 1, "C1")
    user = await db.get_user(db_path, 1)
    assert user is not None
    assert user.level == "C1"


async def test_update_user_notifications(db_path: Path) -> None:
    await db.create_user(db_path, 1)
    await db.update_user_notifications(
        db_path,
        1,
        enabled=True,
        notify_count=2,
        notify_times=["08:00", "20:00"],
    )
    user = await db.get_user(db_path, 1)
    assert user is not None
    assert user.notifications_enabled is True
    assert user.notify_count == 2
    assert user.notify_times == ["08:00", "20:00"]


async def test_get_users_with_notifications(db_path: Path) -> None:
    await db.create_user(db_path, 1)
    await db.create_user(db_path, 2)
    await db.update_user_notifications(
        db_path, 1, enabled=True, notify_count=1, notify_times=["09:00"]
    )

    users = await db.get_users_with_notifications(db_path)
    assert len(users) == 1
    assert users[0].user_id == 1


async def test_word_progress_upsert_and_due(db_path: Path) -> None:
    await db.create_user(db_path, 1, level="A1")
    progress = WordProgress(
        id=0,
        user_id=1,
        word_sr="здраво",
        level="A1",
        ease_factor=2.5,
        interval_days=1,
        next_review=100,
        error_count=0,
        correct_count=1,
        last_seen=50,
    )
    saved = await db.upsert_word_progress(db_path, progress)
    assert saved.id > 0

    fetched = await db.get_word_progress(db_path, 1, "здраво", "A1")
    assert fetched is not None
    assert fetched.correct_count == 1

    due = await db.get_due_word_progress(db_path, 1, "A1", now=200)
    assert len(due) == 1

    not_due = await db.get_due_word_progress(db_path, 1, "A1", now=50)
    assert len(not_due) == 0

    seen = await db.get_seen_word_srs(db_path, 1, "A1")
    assert seen == {"здраво"}


async def test_session_lifecycle(db_path: Path) -> None:
    await db.create_user(db_path, 1)
    session = await db.create_session(db_path, 1, "sr_ru")
    assert session.ended_at is None
    assert session.total == 0

    await db.update_session(db_path, session.id, correct=4, total=5)
    await db.end_session(db_path, session.id)


async def test_get_user_stats(db_path: Path) -> None:
    await db.create_user(db_path, 1, level="A2")
    await db.upsert_word_progress(
        db_path,
        WordProgress(
            id=0,
            user_id=1,
            word_sr="дан",
            level="A2",
            ease_factor=2.5,
            interval_days=1,
            next_review=10,
            error_count=1,
            correct_count=3,
            last_seen=5,
        ),
    )
    await db.upsert_word_progress(
        db_path,
        WordProgress(
            id=0,
            user_id=1,
            word_sr="ноћ",
            level="A2",
            ease_factor=2.5,
            interval_days=5,
            next_review=1000,
            error_count=0,
            correct_count=2,
            last_seen=5,
        ),
    )

    stats = await db.get_user_stats(db_path, 1, "A2", now=100)
    assert stats.words_learned == 2
    assert stats.total_answers == 6
    assert stats.correct_answers == 5
    assert stats.accuracy == pytest.approx(83.333, rel=0.01)
    assert stats.words_due == 1
