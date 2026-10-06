"""/start and /help (same text). Unknown commands also show help."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.common import ensure_allowed, state

HELP_TEXT = (
    "Привет. Я пересылаю твои сообщения в Gemini Flash-Lite и показываю ответ по мере генерации.\n"
    "\n"
    "Просто напиши вопрос текстом.\n"
    "• Ответ печатается в реальном времени, кнопка Stop в черновике останавливает генерацию.\n"
    "• Каждое сообщение — отдельный запрос: я не помню предыдущий диалог.\n"
    "• Длинные ответы приходят несколькими сообщениями.\n"
    "• Понимаю только текст.\n"
    "\n"
    "Модель: {model}"
)


def help_text(model: str) -> str:
    return HELP_TEXT.format(model=model)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_allowed(update, context):
        return
    await update.effective_message.reply_text(help_text(state(context).settings.gemini_model))
