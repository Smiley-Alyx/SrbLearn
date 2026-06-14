"""Сохранение обращений пользователей в JSONL-файл."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path


def _append_entry(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def save_support_message(
    path: Path,
    *,
    user_id: int,
    username: str | None,
    message: str,
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "username": username,
        "message": message,
    }
    await asyncio.to_thread(_append_entry, path, entry)
