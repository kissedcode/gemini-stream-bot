"""Whitelist check (SPEC: Детали: Модель доступа)."""
from __future__ import annotations

from src.config import Settings


def is_allowed(settings: Settings, user_id: int | None, username: str | None) -> bool:
    if user_id is None:
        return False
    if user_id == settings.owner_id or user_id in settings.allowed_user_ids:
        return True
    return bool(username) and username.lstrip("@").lower() in settings.allowed_username_set
