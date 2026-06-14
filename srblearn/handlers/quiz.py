"""Обработчик /quiz — оба режима викторины."""

from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler

from srblearn import db
from srblearn.handlers.common import BTN_QUIZ_FILTER, get_db_path, inline_keyboard
from srblearn.models import QuizQuestion
from srblearn.quiz_engine import (
    QUIZ_MODE_RU_SR,
    QUIZ_MODE_SR_RU,
    QuizSession,
)

MODE_LABELS = {
    QUIZ_MODE_SR_RU: "сербский → русский",
    QUIZ_MODE_RU_SR: "русский → сербский",
}


def _clear_quiz_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        "quiz_engine",
        "quiz_session_id",
        "quiz_correct",
        "quiz_total",
        "quiz_question",
        "quiz_answered",
        "quiz_mode",
    ):
        context.user_data.pop(key, None)


def _correct_answer_text(question: QuizQuestion) -> str:
    if question.mode == QUIZ_MODE_SR_RU:
        return question.word.ru
    return question.word.sr


def _question_keyboard(question: QuizQuestion):
    buttons = [[(option, f"quiz:ans:{index}")] for index, option in enumerate(question.options)]
    buttons.append([("Закончить", "quiz:end")])
    return inline_keyboard(buttons)


def _after_answer_keyboard():
    return inline_keyboard(
        [
            [("Следующее слово", "quiz:next"), ("Закончить", "quiz:end")],
        ]
    )


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    await _finish_active_session(update, context, silent=True)

    keyboard = inline_keyboard(
        [
            [
                ("🇷🇸 → 🇷🇺 Сербский → Русский", f"quiz:mode:{QUIZ_MODE_SR_RU}"),
            ],
            [
                ("🇷🇺 → 🇷🇸 Русский → Сербский", f"quiz:mode:{QUIZ_MODE_RU_SR}"),
            ],
        ]
    )
    await update.message.reply_text(
        "Выберите режим викторины:",
        reply_markup=keyboard,
    )


async def quiz_mode_selected(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None or query.data is None or update.effective_user is None:
        return

    await query.answer()
    mode = query.data.split(":")[-1]
    db_path = get_db_path(context)
    user = await db.get_or_create_user(
        db_path,
        update.effective_user.id,
        update.effective_user.username,
    )

    session_row = await db.create_session(db_path, user.user_id, mode)
    engine = QuizSession(db_path, user.user_id, user.level, mode)
    await engine.load_vocabulary()

    context.user_data["quiz_engine"] = engine
    context.user_data["quiz_session_id"] = session_row.id
    context.user_data["quiz_correct"] = 0
    context.user_data["quiz_total"] = 0
    context.user_data["quiz_answered"] = False
    context.user_data["quiz_mode"] = mode

    question = await engine.get_next_question()
    if question is None:
        await query.edit_message_text("Нет доступных слов для этого уровня.")
        _clear_quiz_state(context)
        return

    context.user_data["quiz_question"] = question
    text = _format_question_text(question)
    await query.edit_message_text(
        text,
        reply_markup=_question_keyboard(question),
        parse_mode="Markdown",
    )


def _format_question_text(question: QuizQuestion) -> str:
    mode_label = MODE_LABELS[question.mode]
    return f"📝 *{mode_label}*\n\nПереведите: *{question.prompt}*"


async def quiz_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return

    if context.user_data.get("quiz_answered"):
        await query.answer("Сначала нажмите «Следующее слово».", show_alert=True)
        return

    question: QuizQuestion | None = context.user_data.get("quiz_question")
    engine: QuizSession | None = context.user_data.get("quiz_engine")
    if question is None or engine is None:
        await query.answer("Сессия не найдена. Нажмите /quiz.", show_alert=True)
        return

    await query.answer()
    selected_index = int(query.data.split(":")[-1])
    is_correct = selected_index == question.correct_index

    await engine.record_answer(question.word.sr, is_correct)

    correct_count = context.user_data.get("quiz_correct", 0)
    total_count = context.user_data.get("quiz_total", 0)
    total_count += 1
    if is_correct:
        correct_count += 1

    context.user_data["quiz_correct"] = correct_count
    context.user_data["quiz_total"] = total_count
    context.user_data["quiz_answered"] = True

    session_id = context.user_data.get("quiz_session_id")
    if session_id is not None:
        db_path = get_db_path(context)
        await db.update_session(
            db_path,
            session_id,
            correct=correct_count,
            total=total_count,
        )

    if is_correct:
        result_text = "✅ Правильно!"
    else:
        result_text = f"❌ Неверно! Правильный ответ: *{_correct_answer_text(question)}*"

    mode_label = MODE_LABELS[question.mode]
    text = (
        f"📝 *{mode_label}*\n\n"
        f"Слово: *{question.prompt}*\n\n"
        f"{result_text}"
    )
    await query.edit_message_text(
        text,
        reply_markup=_after_answer_keyboard(),
        parse_mode="Markdown",
    )


async def quiz_next(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    engine: QuizSession | None = context.user_data.get("quiz_engine")
    if engine is None:
        await query.answer("Сессия не найдена. Нажмите /quiz.", show_alert=True)
        return

    await query.answer()
    question = await engine.get_next_question()
    if question is None:
        await query.edit_message_text(
            "Больше нет слов для повторения. Нажмите «Закончить» для итога.",
            reply_markup=inline_keyboard([[("Закончить", "quiz:end")]]),
        )
        return

    context.user_data["quiz_question"] = question
    context.user_data["quiz_answered"] = False
    await query.edit_message_text(
        _format_question_text(question),
        reply_markup=_question_keyboard(question),
        parse_mode="Markdown",
    )


async def quiz_end(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    summary = await _finish_active_session(update, context)
    if not summary:
        summary = "Сессия завершена. Ответов не было."
    await query.edit_message_text(summary, parse_mode="Markdown")


async def _finish_active_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    silent: bool = False,
) -> str:
    correct = context.user_data.get("quiz_correct", 0)
    total = context.user_data.get("quiz_total", 0)
    session_id = context.user_data.get("quiz_session_id")

    if session_id is not None:
        db_path = get_db_path(context)
        if total > 0:
            await db.update_session(db_path, session_id, correct=correct, total=total)
        await db.end_session(db_path, session_id)

    _clear_quiz_state(context)

    if silent or total == 0:
        return ""

    accuracy = correct / total * 100
    return (
        f"🏁 *Итог сессии*\n\n"
        f"Правильных: {correct} из {total}\n"
        f"Точность: {accuracy:.1f}%"
    )


def get_handlers() -> list:
    return [
        CommandHandler("quiz", quiz_command),
        MessageHandler(BTN_QUIZ_FILTER, quiz_command),
        CallbackQueryHandler(quiz_mode_selected, pattern=r"^quiz:mode:"),
        CallbackQueryHandler(quiz_answer, pattern=r"^quiz:ans:"),
        CallbackQueryHandler(quiz_next, pattern=r"^quiz:next$"),
        CallbackQueryHandler(quiz_end, pattern=r"^quiz:end$"),
    ]
