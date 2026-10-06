"""Gemini streaming client (SPEC: Детали: Внешние интеграции)."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from google import genai
from google.genai import errors, types

log = logging.getLogger(__name__)

RETRY_DELAY_SEC = 2.0


def _retryable(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    return isinstance(code, int) and (code == 429 or code >= 500)


class GeminiService:
    def __init__(self, api_key: str, model: str, system_prompt: str = "") -> None:
        self.model = model
        self._client = genai.Client(api_key=api_key)
        self._config = (
            types.GenerateContentConfig(system_instruction=system_prompt)
            if system_prompt.strip()
            else None
        )

    async def stream_answer(self, prompt: str) -> AsyncIterator[str]:
        """Yield text pieces of the answer. One retry on 429/5xx before the first chunk."""
        for attempt in range(2):
            started = False
            try:
                stream = await self._client.aio.models.generate_content_stream(
                    model=self.model, contents=prompt, config=self._config
                )
                async for chunk in stream:
                    started = True
                    text = chunk.text
                    if text:
                        yield text
                return
            except errors.APIError as exc:
                if not started and attempt == 0 and _retryable(exc):
                    log.warning("gemini %s before first chunk, retrying", getattr(exc, "code", "?"))
                    await asyncio.sleep(RETRY_DELAY_SEC)
                    continue
                raise
