"""Обработчики команд бота."""

from srblearn.handlers import quiz, settings, start, support

__all__ = ["quiz", "settings", "start", "support"]


def get_all_handlers() -> list:
    return (
        start.get_handlers()
        + settings.get_handlers()
        + support.get_handlers()
        + quiz.get_handlers()
    )
