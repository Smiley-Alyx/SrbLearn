"""Обработчики команд бота."""

from srblearn.handlers import quiz, settings, start

__all__ = ["quiz", "settings", "start"]


def get_all_handlers() -> list:
    return start.get_handlers() + settings.get_handlers() + quiz.get_handlers()
