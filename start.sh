#!/bin/sh
set -eu

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DOCKER_DIR="$PROJECT_ROOT/docker"
PATH="/usr/local/bin:/opt/homebrew/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
export PATH

if [ ! -f "$DOCKER_DIR/.env" ]; then
  cp "$DOCKER_DIR/.env.example" "$DOCKER_DIR/.env"
  echo "Created docker/.env from docker/.env.example."
  echo "Edit docker/.env and replace all change_me values, then run ./start.sh again."
  exit 1
fi

if [ -d "$PROJECT_ROOT/data/postgres" ]; then
  # External macOS volumes can create AppleDouble files that break Postgres startup.
  if command -v dot_clean >/dev/null 2>&1; then
    dot_clean -m "$PROJECT_ROOT/data/postgres" 2>/dev/null || true
  fi
  find "$PROJECT_ROOT/data/postgres" -name '._*' -type f -delete 2>/dev/null || true
fi

cd "$DOCKER_DIR"
docker compose --env-file .env up -d
docker compose --env-file .env ps
