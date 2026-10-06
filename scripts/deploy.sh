#!/usr/bin/env bash
# Build on the Mac -> push to GHCR -> SSH restart on the droplet.
# DROPLET_HOST is an alias from ~/.ssh/config, e.g.: DROPLET_HOST=bots-droplet ./scripts/deploy.sh
set -euo pipefail

BOT_NAME="gemini-stream-bot"
IMAGE="ghcr.io/kissedcode/${BOT_NAME}"
DROPLET_HOST="${DROPLET_HOST:?set DROPLET_HOST to the ssh alias of the droplet}"
DROPLET_BOT_DIR="/opt/bots/${BOT_NAME}"

git rev-parse --git-dir >/dev/null 2>&1 || { echo "Run from the repo root" >&2; exit 1; }
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[[ "${BRANCH}" == "main" ]] || echo "warning: building from branch '${BRANCH}'" >&2
GIT_SHA="$(git rev-parse --short HEAD)"

echo "==> Build ${IMAGE}:${GIT_SHA} (linux/amd64)"
docker build --platform linux/amd64 -t "${IMAGE}:${GIT_SHA}" -t "${IMAGE}:latest" .

echo "==> Push"
docker push "${IMAGE}:${GIT_SHA}"
docker push "${IMAGE}:latest"

echo "==> Sync docker-compose.yml"
ssh "${DROPLET_HOST}" "mkdir -p ${DROPLET_BOT_DIR}"
scp docker-compose.yml "${DROPLET_HOST}:${DROPLET_BOT_DIR}/"
ssh "${DROPLET_HOST}" "test -f ${DROPLET_BOT_DIR}/.env" \
  || { echo "Missing ${DROPLET_BOT_DIR}/.env on the droplet (copy it once, chmod 600)" >&2; exit 1; }

echo "==> Restart"
ssh "${DROPLET_HOST}" "cd ${DROPLET_BOT_DIR} && docker compose pull && docker compose up -d"

echo "==> Logs"
sleep 3
ssh "${DROPLET_HOST}" "cd ${DROPLET_BOT_DIR} && docker compose logs --tail=50"
echo "==> Deployed ${IMAGE}:${GIT_SHA}"
