# gemini-stream-bot

Private Telegram bot that forwards text messages to Gemini Flash-Lite and streams the answer back with Telegram's native draft streaming (`sendMessageDraft`), including the Stop button (`can_stop` / `stopped_message_generation`, Bot API 10.3).

Behaviour is defined in [SPEC.md](SPEC.md) (in Russian) — it is the source of truth.

## Configuration

Locally: `.env` (never committed), see [.env.example](.env.example). Required: `BOT_TOKEN`, `GEMINI_API_KEY`, `ALLOWED_USERNAMES` (comma-separated, without `@`). Optional: `GEMINI_MODEL` (default `gemini-3.5-flash-lite`), `GEMINI_SYSTEM_PROMPT`, `GEMINI_TIMEOUT_SEC`, `RATE_LIMIT_PER_MINUTE`, `DRAFT_INTERVAL_MS`.

In production all secrets live in GitHub Actions secrets of the `production` environment (limited to `main`).

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

## CI/CD (GitHub Actions)

`.github/workflows/ci-cd.yml`:

- every PR: ruff + pytest (fork PRs never get secrets: `pull_request`, not `pull_request_target`);
- push to `main`: tests → build `ghcr.io/kissedcode/gemini-stream-bot:{sha,latest}` → deploy to the droplet over SSH (writes `.env` from secrets, `docker compose pull && up -d`, checks `Application started`).

One-time setup of secrets (on the Mac, needs `gh` and ssh access to the droplet):

```bash
bash scripts/setup-github-secrets.sh
```

Secrets: `BOT_TOKEN`, `GEMINI_API_KEY`, `ALLOWED_USERNAMES`, `DROPLET_HOST`, `DROPLET_USER`, `DROPLET_SSH_KEY`, `DROPLET_KNOWN_HOSTS`. Optional repo/environment variables: `GEMINI_MODEL`, `GEMINI_SYSTEM_PROMPT`.

Logs: `DROPLET_HOST=<ssh-alias> ./scripts/logs.sh`

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
