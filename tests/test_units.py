from src.access import is_allowed
from src.config import Settings
from src.services.formatting import split_text, to_markdown_v2
from src.services.rate_limit import RateLimiter


def make_settings(**kw):
    base = dict(bot_token="x", gemini_api_key="y", owner_id=1)
    base.update(kw)
    return Settings(_env_file=None, **base)


def test_access_rules():
    s = make_settings(allowed_users="2, 3", allowed_usernames="@Alice,bob")
    assert is_allowed(s, 1, None)
    assert is_allowed(s, 3, None)
    assert is_allowed(s, 9, "alice")
    assert is_allowed(s, 9, "BOB")
    assert not is_allowed(s, 9, "eve")
    assert not is_allowed(s, 9, None)
    assert not is_allowed(s, None, "alice")


def test_settings_repr_hides_secrets():
    s = make_settings(bot_token="SECRET", gemini_api_key="KEY")
    assert "SECRET" not in repr(s) and "KEY" not in str(s)


def test_split_prefers_paragraph():
    text = "a" * 3000 + "\n\n" + "b" * 1500
    head, tail = split_text(text, 4000)
    assert head == "a" * 3000 and tail == "b" * 1500


def test_split_hard_cut():
    text = "x" * 5000
    head, tail = split_text(text, 4000)
    assert len(head) == 4000 and head + tail == text


def test_split_short():
    assert split_text("hi", 4000) == ("hi", "")


def test_markdown():
    assert to_markdown_v2("**bold**") == "*bold*"


def test_rate_limiter():
    t = [0.0]
    rl = RateLimiter(2, 60, clock=lambda: t[0])
    assert rl.hit(1) and rl.hit(1) and not rl.hit(1)
    assert rl.hit(2)
    t[0] = 61
    assert rl.hit(1)
