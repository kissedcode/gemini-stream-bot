"""Entry point: builds the Application, registers handlers, runs long polling."""
from __future__ import annotations

import asyncio
import logging
import signal

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from src.config import Settings, load_settings
from src.handlers.commands import help_command
from src.handlers.common import BotState
from src.handlers.messages import on_non_text, on_text
from src.handlers.stop import on_stop_generation
from src.services.gemini import GeminiService
from src.services.rate_limit import RateLimiter

log = logging.getLogger("bot")

ALLOWED_UPDATES = [Update.MESSAGE, "stopped_message_generation"]
COMMANDS = [BotCommand("start", "Справка"), BotCommand("help", "Справка")]


def _setup_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    # httpx logs request URLs, which contain the bot token
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)


async def _shutdown(app: Application) -> None:
    st: BotState = app.bot_data["state"]
    gens = list(st.active.values())
    if gens:
        log.info("shutdown: finalizing %d active answer(s)", len(gens))
        await asyncio.gather(*(g.cancel("shutdown") for g in gens), return_exceptions=True)
    app.stop_running()


async def _post_init(app: Application) -> None:
    await app.bot.set_my_commands(COMMANDS)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.ensure_future(_shutdown(app)))
    log.info("Application started (model=%s)", app.bot_data["state"].settings.gemini_model)


def build_application(settings: Settings) -> Application:
    app = (
        ApplicationBuilder()
        .token(settings.bot_token)
        .concurrent_updates(True)
        .post_init(_post_init)
        .build()
    )
    app.bot_data["state"] = BotState(
        settings=settings,
        gemini=GeminiService(
            settings.gemini_api_key, settings.gemini_model, settings.gemini_system_prompt
        ),
        limiter=RateLimiter(settings.rate_limit_per_minute),
    )

    private = filters.ChatType.PRIVATE
    app.add_handler(TypeHandler(Update, on_stop_generation), group=-1)
    app.add_handler(CommandHandler(["start", "help"], help_command, filters=private))
    app.add_handler(MessageHandler(private & filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(MessageHandler(private & filters.COMMAND, help_command))
    app.add_handler(
        MessageHandler(private & ~filters.TEXT & ~filters.StatusUpdate.ALL, on_non_text)
    )
    return app


def main() -> None:
    settings = load_settings()
    _setup_logging(settings.log_level)
    app = build_application(settings)
    # own signal handlers (see _post_init) finalize in-flight answers before stopping
    app.run_polling(allowed_updates=ALLOWED_UPDATES, stop_signals=None)


if __name__ == "__main__":
    main()
