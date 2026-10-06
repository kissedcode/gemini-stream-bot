import asyncio

from telegram.error import BadRequest

from src.services import streamer as s
from src.services.streamer import Generation


class FakeBot:
    def __init__(self, reject_markdown=False):
        self.drafts, self.messages = [], []
        self.reject_markdown = reject_markdown

    async def send_message_draft(self, chat_id, draft_id, text, api_kwargs=None):
        assert api_kwargs == {"can_stop": True}
        self.drafts.append((draft_id, text))
        return True

    async def send_message(self, chat_id, text, parse_mode=None, reply_parameters=None):
        if parse_mode and self.reject_markdown:
            raise BadRequest("can't parse entities")
        self.messages.append(
            dict(text=text, md=bool(parse_mode), reply=reply_parameters.message_id if reply_parameters else None)
        )


async def gen_of(*pieces, delay=0.0, fail=None):
    for p in pieces:
        if delay:
            await asyncio.sleep(delay)
        yield p
    if fail:
        raise fail


def make(bot, **kw):
    return Generation(bot, chat_id=10, reply_to=5, draft_interval_sec=kw.get("interval", 0), timeout_sec=kw.get("timeout", 5))


async def test_happy_path_streams_and_finalizes():
    bot = FakeBot()
    g = make(bot)
    status = await g.run(gen_of("Hello ", "**world**"))
    assert status == "ok"
    assert bot.drafts[0][1] == ""  # Thinking placeholder
    assert bot.drafts[-1][1] == "Hello **world**"
    assert bot.messages == [dict(text="Hello *world*", md=True, reply=5)]


async def test_markdown_fallback_to_plain():
    bot = FakeBot(reject_markdown=True)
    await make(bot).run(gen_of("**x**"))
    assert bot.messages == [dict(text="**x**", md=False, reply=5)]


async def test_long_answer_split_reply_only_first():
    bot = FakeBot()
    para = "y" * 3000 + "\n\n"
    await make(bot).run(gen_of(para, para, para))
    assert len(bot.messages) == 3
    assert [m["reply"] for m in bot.messages] == [5, None, None]
    assert "".join(m["text"] for m in bot.messages).count("y") == 9000
    assert len({d for d, _ in bot.drafts}) == 3


async def test_empty_answer():
    bot = FakeBot()
    assert await make(bot).run(gen_of()) == "empty"
    assert bot.messages[-1]["text"] == s.EMPTY_TEXT


async def test_error_keeps_partial():
    bot = FakeBot()
    status = await make(bot).run(gen_of("part", fail=RuntimeError("boom")))
    assert status == "error"
    assert [m["text"] for m in bot.messages] == ["part", s.ERROR_TEXT]


async def test_timeout():
    bot = FakeBot()
    status = await make(bot, timeout=0.05).run(gen_of("a", "b", delay=0.2))
    assert status == "error"
    assert bot.messages[-1]["text"] == s.ERROR_TEXT


async def test_stop_keeps_partial_with_mark():
    bot = FakeBot()
    g = make(bot)
    task = asyncio.create_task(g.run(gen_of("one ", "two ", "three", delay=0.05)))
    await asyncio.sleep(0.12)
    await g.cancel("stopped")
    assert await task == "stopped"
    text = bot.messages[-1]["text"]
    assert text.startswith("one") and text.endswith(s.STOPPED_MARK) and "three" not in text


async def test_stop_before_any_text():
    bot = FakeBot()
    g = make(bot)
    task = asyncio.create_task(g.run(gen_of("late", delay=1)))
    await asyncio.sleep(0.02)
    await g.cancel("stopped")
    assert await task == "stopped"
    assert bot.messages[-1]["text"] == s.STOPPED_MARK


async def test_draft_throttle():
    bot = FakeBot()
    g = make(bot, interval=10)
    await g.run(gen_of("a", "b", "c"))
    # placeholder + first chunk; the rest throttled, final message has everything
    assert len(bot.drafts) == 2
    assert bot.messages[-1]["text"] == "abc"
