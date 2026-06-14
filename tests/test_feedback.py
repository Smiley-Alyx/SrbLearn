"""Тесты feedback."""

from __future__ import annotations

from pathlib import Path

import pytest

from srblearn import feedback

pytestmark = pytest.mark.asyncio


async def test_save_support_message(tmp_path: Path) -> None:
    path = tmp_path / "support.jsonl"
    await feedback.save_support_message(
        path,
        user_id=42,
        username="tester",
        message="Бот не отвечает на /quiz",
    )

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert "Бот не отвечает" in lines[0]
    assert '"user_id": 42' in lines[0]
