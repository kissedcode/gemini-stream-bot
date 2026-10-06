"""Text -> Gemini stream; non-text -> refusal."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.common import ensure_allowed, state
from src.services.streamer import Generation

RATE_LIMITED = "Слишком много запросов. Подожди минуту и попробуй снова."
NON_TEXT = "Пока я понимаю только текстовые сообщения."


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_allowed(update, context):
        return
    st = state(context)
    message = update.effective_message
    chat_id = message.chat_id

    if not st.limiter.hit(update.effective_user.id):
        await message.reply_text(RATE_LIMITED)
        return

    previous = st.active.get(chat_id)
    if previous is not None:
        await previous.cancel("superseded")

    gen = Generation(
        bot=context.bot,
        chat_id=chat_id,
        reply_to=message.message_id,
        draft_interval_sec=st.settings.draft_interval_ms / 1000,
        timeout_sec=st.settings.gemini_timeout_sec,
    )
    st.active[chat_id] = gen
    try:
        await gen.run(st.gemini.stream_answer(message.text))
    finally:
        if st.active.get(chat_id) is gen:
            del st.active[chat_id]


async def on_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_allowed(update, context):
        return
    await update.effective_message.reply_text(NON_TEXT)
