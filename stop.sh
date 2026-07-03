#!/bin/sh
set -eu

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DOCKER_DIR="$PROJECT_ROOT/docker"
PATH="/usr/local/bin:/opt/homebrew/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
export PATH

pkill -f "resend_webhook_server.py" 2>/dev/null && echo "Stopped Resend webhook receiver." || true

cd "$DOCKER_DIR"
docker compose --env-file .env down
