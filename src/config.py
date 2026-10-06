"""Settings read from the environment (.env locally, env_file in docker compose)."""
from __future__ import annotations

from functools import cached_property

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
    gemini_model: str = "gemini-3.8-flash"
    gemini_system_prompt: str = ""
    gemini_timeout_sec: float = 120

    owner_id: int
    # CSV strings; parsed by properties below (keeps pydantic from JSON-decoding them)
    allowed_users: str = ""
    allowed_usernames: str = ""

    rate_limit_per_minute: int = 20
    draft_interval_ms: int = 300

    tz: str = "Europe/Luxembourg"
    log_level: str = "INFO"

    @cached_property
    def allowed_user_ids(self) -> frozenset[int]:
        return frozenset(int(x) for x in self.allowed_users.split(",") if x.strip())

    @cached_property
    def allowed_username_set(self) -> frozenset[str]:
        return frozenset(
            x.strip().lstrip("@").lower() for x in self.allowed_usernames.split(",") if x.strip()
        )

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
