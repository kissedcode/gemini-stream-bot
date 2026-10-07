"""Whitelist check (SPEC: Детали: Модель доступа). Usernames only."""
from __future__ import annotations

from src.config import Settings


def is_allowed(settings: Settings, username: str | None) -> bool:
    return bool(username) and username.lstrip("@").lower() in settings.allowed_username_set
