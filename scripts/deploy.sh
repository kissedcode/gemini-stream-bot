#!/usr/bin/env bash
# Deploy = git pull + docker compose build on the droplet (same as the other bots on it).
# DROPLET_HOST is an alias from ~/.ssh/config, e.g.: DROPLET_HOST=kissed.droplet ./scripts/deploy.sh
set -euo pipefail

BOT_NAME="gemini-stream-bot"
REPO_URL="https://github.com/kissedcode/${BOT_NAME}.git"
DROPLET_HOST="${DROPLET_HOST:?set DROPLET_HOST to the ssh alias of the droplet}"
DIR="/opt/${BOT_NAME}"

ssh "${DROPLET_HOST}" bash -s <<REMOTE
set -euo pipefail
if [ ! -d "${DIR}/.git" ]; then
  mkdir -p "${DIR}"
  git clone --quiet "${REPO_URL}" "${DIR}.tmp" && cp -a "${DIR}.tmp/." "${DIR}/" && rm -rf "${DIR}.tmp"
fi
cd "${DIR}"
test -f .env || { echo "Missing ${DIR}/.env (create it once, chmod 600)" >&2; exit 1; }
git fetch --quiet origin main && git reset --quiet --hard origin/main
docker compose up -d --build
sleep 4
docker compose logs --tail=30
echo "Deployed \$(git rev-parse --short HEAD)"
REMOTE
