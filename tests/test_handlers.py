from telegram import Update

from src.handlers.commands import help_text
from src.handlers.stop import extract_stop


def test_extract_stop_from_api_kwargs():
    u = Update.de_json(
        {"update_id": 1, "stopped_message_generation": {"chat": {"id": 5, "type": "private"}, "draft_id": 7}},
        None,
    )
    assert extract_stop(u)["draft_id"] == 7


def test_extract_stop_absent():
    assert extract_stop(Update.de_json({"update_id": 1}, None)) is None


def test_help_contains_model():
    assert help_text("gemini-3.5-flash-lite").endswith("Модель: gemini-3.5-flash-lite")


def test_build_application_registers_handlers():
    from src.config import load_settings
    from src.main import build_application

    app = build_application(load_settings())
    assert -1 in app.handlers and 0 in app.handlers
    assert len(app.handlers[0]) == 4
