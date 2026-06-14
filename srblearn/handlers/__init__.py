"""Обработчики команд бота."""

from srblearn.handlers import settings, start

__all__ = ["settings", "start"]


def get_all_handlers() -> list:
    return start.get_handlers() + settings.get_handlers()
