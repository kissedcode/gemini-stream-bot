"""Markdown -> Telegram MarkdownV2 and splitting of long texts."""
from __future__ import annotations

import logging

import telegramify_markdown

log = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096
SPLIT_AT = 4000


def split_text(text: str, limit: int = SPLIT_AT) -> tuple[str, str]:
    """Split text into (head, tail) so that len(head) <= limit.

    Cuts at the last paragraph break, then line break, then space; otherwise hard cut.
    """
    if len(text) <= limit:
        return text, ""
    window = text[:limit]
    for sep in ("\n\n", "\n", " "):
        idx = window.rfind(sep)
        if idx > 0:
            return text[:idx].rstrip(), text[idx + len(sep):].lstrip("\n")
    return window, text[limit:]


def to_markdown_v2(text: str) -> str | None:
    """Convert model Markdown to MarkdownV2. Returns None if conversion fails."""
    try:
        return telegramify_markdown.markdownify(text)
    except Exception as exc:  # library edge cases must never lose the answer
        log.warning("markdown conversion failed: %s", type(exc).__name__)
        return None
