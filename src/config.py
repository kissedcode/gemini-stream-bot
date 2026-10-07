"""Settings read from the environment (.env locally, env_file in docker compose)."""
from __future__ import annotations

from functools import cached_property

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str
    gemini_api_key: str
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_system_prompt: str = ""
    gemini_timeout_sec: float = 120

    # CSV of Telegram usernames without @ (required; parsed below to keep pydantic from JSON-decoding)
    allowed_usernames: str

    rate_limit_per_minute: int = 20
    draft_interval_ms: int = 300

    tz: str = "Europe/Luxembourg"
    log_level: str = "INFO"

    @cached_property
    def allowed_username_set(self) -> frozenset[str]:
        return frozenset(
            x.strip().lstrip("@").lower() for x in self.allowed_usernames.split(",") if x.strip()
        )

    @model_validator(mode="after")
    def _whitelist_not_empty(self) -> "Settings":
        if not self.allowed_username_set:
            raise ValueError("allowed_usernames is empty")
        return self

    def __repr__(self) -> str:  # never print secrets
        return f"Settings(model={self.gemini_model!r})"

    __str__ = __repr__


def load_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as exc:  # pydantic ValidationError; show field names only, never values
        missing = []
        for err in getattr(exc, "errors", lambda: [])():
            missing.append(".".join(str(p) for p in err.get("loc", ())).upper())
        raise SystemExit(
            "Invalid or missing environment variables: " + (", ".join(missing) or type(exc).__name__)
        ) from None
