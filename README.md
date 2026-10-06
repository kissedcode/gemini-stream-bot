# gemini-stream-bot

Private Telegram bot that forwards text messages to Gemini Flash-Lite and streams the answer back with Telegram's native draft streaming (`sendMessageDraft`), including the Stop button (`can_stop` / `stopped_message_generation`, Bot API 10.3).

Behaviour is defined in [SPEC.md](SPEC.md) (in Russian) — it is the source of truth.

## Configuration

All configuration is in `.env` (never committed). See [.env.example](.env.example).

| Variable | Required | Default |
|---|---|---|
| `BOT_TOKEN` | yes | — |
| `GEMINI_API_KEY` | yes | — |
| `OWNER_ID` | yes | — |
| `ALLOWED_USERS` / `ALLOWED_USERNAMES` | no | empty |
| `GEMINI_MODEL` | no | `gemini-3.5-flash-lite` |
| `GEMINI_SYSTEM_PROMPT` | no | empty |
| `GEMINI_TIMEOUT_SEC` | no | `120` |
| `RATE_LIMIT_PER_MINUTE` | no | `20` |
| `DRAFT_INTERVAL_MS` | no | `300` |

## Run locally

```bash
cp .env.example .env   # fill in the secrets
docker compose up --build
```

Without Docker:

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m src.main
```

## Tests

```bash
pytest && ruff check src tests
```

## Deploy (from the Mac)

The image is built on the droplet from `main`. One-time: create `/opt/gemini-stream-bot/.env` (`chmod 600`).

```bash
DROPLET_HOST=<ssh-alias> ./scripts/deploy.sh
DROPLET_HOST=<ssh-alias> ./scripts/logs.sh
```

## Layout

```text
src/
├── main.py              # Application, handlers, setMyCommands, polling, graceful shutdown
├── config.py            # pydantic-settings
├── access.py            # whitelist
├── handlers/            # /start,/help · text/non-text · Stop update
└── services/
    ├── gemini.py        # google-genai streaming
    ├── streamer.py      # draft throttling, splitting, finalization, cancel
    ├── formatting.py    # Markdown -> MarkdownV2, split_text
    └── rate_limit.py
```
