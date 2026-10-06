# gemini-stream-bot

Telegram bot that forwards text messages to Gemini Flash and streams the answer back using Telegram's native draft streaming (`sendMessageDraft`, Bot API 9.3+), with a Stop button (`can_stop`, Bot API 10.3).

Status: specification only. See [SPEC.md](SPEC.md) (in Russian) — it is the source of truth for behaviour.

## Quick start (after implementation)

```bash
cp .env.example .env   # fill BOT_TOKEN, GEMINI_API_KEY, OWNER_ID, whitelist
docker compose up --build
```

Secrets and the whitelist live only in `.env` and are never committed.
