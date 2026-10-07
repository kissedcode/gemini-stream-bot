"""Shared state and access helpers for handlers."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from telegram import Update
from telegram.ext import ContextTypes

from src.access import is_allowed
from src.config import Settings
from src.services.gemini import GeminiService
from src.services.rate_limit import RateLimiter
from src.services.streamer import Generation

log = logging.getLogger(__name__)

ACCESS_DENIED = "Доступ закрыт."


@dataclass
class BotState:
    settings: Settings
    gemini: GeminiService
    limiter: RateLimiter
    active: dict[int, Generation] = field(default_factory=dict)


def state(context: ContextTypes.DEFAULT_TYPE) -> BotState:
    return context.application.bot_data["state"]


async def ensure_allowed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """True if the sender is whitelisted; otherwise replies 'Доступ закрыт.'."""
    user = update.effective_user
    if is_allowed(state(context).settings, user.username if user else None):
        return True
    log.warning("access denied user=%s", user.id if user else None)
    if update.effective_message:
        await update.effective_message.reply_text(ACCESS_DENIED)
    return False
