#!/usr/bin/env bash
# Tail bot logs on the droplet: DROPLET_HOST=kissed.droplet ./scripts/logs.sh [lines]
set -euo pipefail
DROPLET_HOST="${DROPLET_HOST:?set DROPLET_HOST to the ssh alias of the droplet}"
ssh "${DROPLET_HOST}" "cd /opt/gemini-stream-bot && docker compose logs -f --tail=${1:-100}"
