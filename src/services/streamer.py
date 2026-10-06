"""Streams a model answer into Telegram via sendMessageDraft and finalizes it with sendMessage.

SPEC: Детали: Основные пользовательские потоки -> Ответ на текстовое сообщение / Остановка.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import AsyncIterator

from telegram import Bot, ReplyParameters
from telegram.constants import ParseMode
from telegram.error import BadRequest, RetryAfter, TelegramError

from src.services.formatting import SPLIT_AT, TELEGRAM_LIMIT, split_text, to_markdown_v2

log = logging.getLogger(__name__)

STOPPED_MARK = "⏹ Остановлено"
ERROR_TEXT = "Не удалось получить ответ от Gemini. Попробуй ещё раз чуть позже."
EMPTY_TEXT = "Gemini не вернул ответ на этот запрос."


def new_draft_id() -> int:
    return random.randint(1, 2**31 - 1)


class Generation:
    """One answer in one private chat. Not reusable."""

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        reply_to: int | None,
        draft_interval_sec: float,
        timeout_sec: float,
        clock=time.monotonic,
    ) -> None:
        self.bot = bot
        self.chat_id = chat_id
        self.reply_to = reply_to
        self.interval = draft_interval_sec
        self.timeout = timeout_sec
        self._clock = clock

        self.draft_id = new_draft_id()
        self.draft_ids: set[int] = {self.draft_id}
        self.current = ""
        self.total_chars = 0
        self.parts_sent = 0
        self.cancel_reason: str | None = None

        self._last_draft_text: str | None = None
        self._next_draft_at = 0.0
        self._inner: asyncio.Task | None = None
        self._done = asyncio.Event()

    # ---------- public API ----------

    async def run(self, chunks: AsyncIterator[str]) -> str:
        """Stream `chunks` to the chat. Returns final status: ok | empty | stopped | error."""
        started = self._clock()
        status = "error"
        try:
            await self._send_draft("", force=True)  # empty text -> "Thinking..." placeholder
            if self.cancel_reason is None:
                self._inner = asyncio.ensure_future(self._consume(chunks))
                try:
                    await asyncio.wait_for(self._inner, self.timeout)
                    status = "ok" if self.total_chars else "empty"
                except asyncio.CancelledError:
                    if self.cancel_reason is None:
                        # the handler task itself was cancelled (shutdown) -> finalize, re-raise
                        self.cancel_reason = "shutdown"
                        await self._finish("stopped")
                        raise
                    status = "stopped"
                except TimeoutError:
                    log.error("gemini timeout after %.0fs", self.timeout)
                except Exception as exc:
                    log.error("gemini stream failed: %s", type(exc).__name__)
            else:
                status = "stopped"
            await self._finish(status)
            return status
        finally:
            await _aclose(chunks)
            log.info(
                "answer chat=%s status=%s chars=%d parts=%d took=%.1fs",
                self.chat_id, status, self.total_chars, self.parts_sent, self._clock() - started,
            )
            self._done.set()

    async def cancel(self, reason: str) -> None:
        """Stop generation (Stop button, new question, shutdown) and wait for finalization."""
        if self._done.is_set():
            return
        if self.cancel_reason is None:
            self.cancel_reason = reason
            if self._inner is not None and not self._inner.done():
                self._inner.cancel()
        await self._done.wait()

    @property
    def done(self) -> bool:
        return self._done.is_set()

    # ---------- internals ----------

    async def _consume(self, chunks: AsyncIterator[str]) -> None:
        async for piece in chunks:
            self.current += piece
            self.total_chars += len(piece)
            while len(self.current) > SPLIT_AT:
                head, tail = split_text(self.current, SPLIT_AT)
                await self._send_final(head)
                self.current = tail
                self.draft_id = new_draft_id()
                self.draft_ids.add(self.draft_id)
                self._last_draft_text = None
            if self.current:
                await self._send_draft(self.current)

    async def _finish(self, status: str) -> None:
        text = self.current
        if status == "stopped":
            text = f"{text.rstrip()}\n\n{STOPPED_MARK}" if text.strip() else STOPPED_MARK
            await self._send_final(text)
        elif status == "ok":
            await self._send_final(text)
        elif status == "empty":
            await self._send_final(EMPTY_TEXT, markdown=False)
        else:  # error
            await self._send_final(text)
            await self._send_final(ERROR_TEXT, markdown=False)
        self.current = ""

    async def _send_draft(self, text: str, force: bool = False) -> None:
        now = self._clock()
        if not force and (now < self._next_draft_at or text == self._last_draft_text):
            return
        try:
            await self.bot.send_message_draft(
                chat_id=self.chat_id,
                draft_id=self.draft_id,
                text=text[:TELEGRAM_LIMIT],
                api_kwargs={"can_stop": True},  # Bot API 10.3, not native in PTB 22.8
            )
            self._last_draft_text = text
            if not force:  # the placeholder must not delay the first real text
                self._next_draft_at = now + self.interval
        except RetryAfter as exc:
            ra = exc.retry_after
            delay = float(ra.total_seconds() if hasattr(ra, "total_seconds") else ra)
            self.interval = max(self.interval, delay)
            self._next_draft_at = now + delay
            log.warning("sendMessageDraft flood control, interval now %.1fs", self.interval)
        except TelegramError as exc:
            self._next_draft_at = now + self.interval
            log.warning("sendMessageDraft failed: %s", exc.__class__.__name__)

    async def _send_final(self, text: str, markdown: bool = True) -> None:
        if not text.strip():
            return
        kwargs = {}
        if self.reply_to is not None:
            kwargs["reply_parameters"] = ReplyParameters(
                message_id=self.reply_to, allow_sending_without_reply=True
            )
        if markdown:
            md = to_markdown_v2(text)
            if md and len(md) <= TELEGRAM_LIMIT:
                try:
                    await self.bot.send_message(
                        self.chat_id, md, parse_mode=ParseMode.MARKDOWN_V2, **kwargs
                    )
                    self._sent()
                    return
                except BadRequest as exc:
                    log.warning("MarkdownV2 rejected, falling back to plain: %s", exc.message[:80])
        try:
            await self.bot.send_message(self.chat_id, text[:TELEGRAM_LIMIT], **kwargs)
            self._sent()
        except TelegramError as exc:
            log.error("sendMessage failed: %s", exc.__class__.__name__)

    def _sent(self) -> None:
        self.parts_sent += 1
        self.reply_to = None  # only the first part is a reply


async def _aclose(chunks: AsyncIterator[str]) -> None:
    aclose = getattr(chunks, "aclose", None)
    if aclose is not None:
        try:
            await aclose()
        except Exception:
            pass
