#!/usr/bin/env bash
# Fill GitHub environment "production" secrets for CI/CD. Run on the Mac from anywhere:
#   bash scripts/setup-github-secrets.sh
# Needs: gh (logged in as the repo owner), ssh access to the droplet via an ~/.ssh/config alias.
# Secret values are never printed and never passed as command-line arguments.
set -euo pipefail

REPO="${REPO:-kissedcode/gemini-stream-bot}"
ENV_NAME="production"
ALIAS="${DROPLET_ALIAS:-kissed.droplet}"            # ssh alias of the droplet
SOURCE_ENV="${SOURCE_ENV:-/opt/english-bot/.env}"    # where to copy GEMINI_API_KEY from

say() { printf '\033[1m==> %s\033[0m\n' "$*"; }
die() { printf 'Ошибка: %s\n' "$*" >&2; exit 1; }
put() { printf '%s' "$2" | gh secret set "$1" --repo "$REPO" --env "$ENV_NAME" >/dev/null && echo "  $1: ok"; }

command -v gh >/dev/null || die "нужен gh (brew install gh)"
gh auth status >/dev/null 2>&1 || die "gh не залогинен: gh auth login"
gh api "repos/$REPO" >/dev/null 2>&1 || die "нет доступа к $REPO"

say "Environment $ENV_NAME (только ветка main)"
gh api -X PUT "repos/$REPO/environments/$ENV_NAME" --input - >/dev/null <<'JSON'
{"deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}
JSON
POLICIES="$(gh api "repos/$REPO/environments/$ENV_NAME/deployment-branch-policies" -q '.branch_policies[].name')"
if ! printf '%s\n' "$POLICIES" | grep -qx main; then
  gh api -X POST "repos/$REPO/environments/$ENV_NAME/deployment-branch-policies" -f name=main -f type=branch >/dev/null
fi

say "Дроплет: $ALIAS"
HOST="$(ssh -G "$ALIAS" | awk '$1=="hostname"{print $2}')"
USER_="$(ssh -G "$ALIAS" | awk '$1=="user"{print $2}')"
[ -n "$HOST" ] && [ -n "$USER_" ] || die "не удалось прочитать hostname/user для $ALIAS из ssh config"
ssh -o BatchMode=yes "$ALIAS" true || die "ssh $ALIAS не работает"
echo "  $USER_@$HOST"

# 1. BOT_TOKEN — hidden input
say "BOT_TOKEN"
read -rsp "  Токен нового бота от @BotFather (ввод скрыт): " BOT_TOKEN; echo
[[ "$BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]{30,}$ ]] || die "не похоже на токен BotFather"
BOT_NAME="$(curl -fsS "https://api.telegram.org/bot${BOT_TOKEN}/getMe" 2>/dev/null \
  | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')" || true
[ -n "$BOT_NAME" ] || die "Telegram не принял токен (getMe)"
echo "  бот: @$BOT_NAME"
put BOT_TOKEN "$BOT_TOKEN"; unset BOT_TOKEN

# 2. GEMINI_API_KEY — copied from the English bot on the droplet
say "GEMINI_API_KEY из $ALIAS:$SOURCE_ENV"
GEMINI_API_KEY="$(ssh "$ALIAS" "grep -E '^GEMINI_API_KEY=' '$SOURCE_ENV' | tail -1 | cut -d= -f2- | tr -d '\"\r'\"'\"")"
[ -n "$GEMINI_API_KEY" ] || die "GEMINI_API_KEY не найден в $SOURCE_ENV"
CODE="$(curl -s -o /dev/null -w '%{http_code}' -H "x-goog-api-key: $GEMINI_API_KEY" \
  https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite)"
[ "$CODE" = 200 ] || die "ключ не работает с gemini-3.5-flash-lite (HTTP $CODE)"
echo "  ключ работает с gemini-3.5-flash-lite"
put GEMINI_API_KEY "$GEMINI_API_KEY"; unset GEMINI_API_KEY

# 3. ALLOWED_USERNAMES
say "ALLOWED_USERNAMES"
DEFAULT_USERS="$(ssh "$ALIAS" "grep -E '^ALLOWED_USERNAMES=' '$SOURCE_ENV' | tail -1 | cut -d= -f2- | tr -d '\"\r'\"'\"" || true)"
read -rp "  Usernames через запятую, без @ [${DEFAULT_USERS}]: " USERS
USERS="$(printf '%s' "${USERS:-$DEFAULT_USERS}" | tr -d ' @')"
[ -n "$USERS" ] || die "пустой whitelist"
put ALLOWED_USERNAMES "$USERS"

# 4. Droplet connection + dedicated deploy key
say "Deploy-ключ для GitHub Actions"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
ssh-keygen -q -t ed25519 -N "" -C "github-actions@${REPO}" -f "$TMP/key"
PUB="$(cat "$TMP/key.pub")"
printf '%s\n' "$PUB" | ssh "$ALIAS" 'umask 077; mkdir -p ~/.ssh; touch ~/.ssh/authorized_keys;
  sed -i "/github-actions@kissedcode\/gemini-stream-bot\$/d" ~/.ssh/authorized_keys; cat >> ~/.ssh/authorized_keys'
echo "  публичный ключ добавлен на дроплет (старый ключ этого репо, если был, удалён)"
put DROPLET_SSH_KEY "$(cat "$TMP/key")"

KNOWN="$(ssh-keygen -F "$HOST" 2>/dev/null | grep -v '^#' || true)"
if [ -z "$KNOWN" ]; then
  KNOWN="$(ssh-keyscan -t ed25519,rsa,ecdsa "$HOST" 2>/dev/null)"
  echo "  known_hosts взят через ssh-keyscan"
fi
[ -n "$KNOWN" ] || die "не удалось получить host key дроплета"
put DROPLET_KNOWN_HOSTS "$KNOWN"
put DROPLET_HOST "$HOST"
put DROPLET_USER "$USER_"

say "Секреты в $REPO / $ENV_NAME"
gh secret list --repo "$REPO" --env "$ENV_NAME"

echo
read -rp "Запустить деплой сейчас? [Y/n] " GO
if [[ "${GO:-Y}" =~ ^[Yy]$ ]]; then
  gh workflow run ci-cd.yml --repo "$REPO" --ref main
  sleep 5
  echo "Ход деплоя: https://github.com/$REPO/actions"
  gh run watch --repo "$REPO" "$(gh run list --repo "$REPO" --workflow ci-cd.yml --event workflow_dispatch --limit 1 --json databaseId -q '.[0].databaseId')" --exit-status \
    && echo "Готово: напиши @$BOT_NAME в личку."
fi
