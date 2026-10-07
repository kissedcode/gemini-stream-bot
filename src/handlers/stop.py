"""Update `stopped_message_generation` (Bot API 10.3): user pressed Stop in a draft."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from src.access import is_allowed
from src.handlers.common import state

log = logging.getLogger(__name__)


def extract_stop(update: Update) -> dict | None:
    native = getattr(update, "stopped_message_generation", None)
    if native is not None:  # future PTB versions
        return native.to_dict() if hasattr(native, "to_dict") else dict(native)
    return (update.api_kwargs or {}).get("stopped_message_generation")


async def on_stop_generation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = extract_stop(update)
    if not data:
        return
    chat = data.get("chat") or {}
    chat_id, draft_id = chat.get("id"), data.get("draft_id")
    st = state(context)
    # MessageGenerationStopped has no `from`: in a private chat chat.username == user's username
    if chat.get("type") != "private" or not is_allowed(st.settings, chat.get("username")):
        raise ApplicationHandlerStop
    gen = st.active.get(chat_id)
    if gen is not None and draft_id in gen.draft_ids:
        log.info("stop requested chat=%s", chat_id)
        await gen.cancel("stopped")
    raise ApplicationHandlerStop
