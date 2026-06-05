#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/docker/.env"
SCHEMA_FILE="$PROJECT_ROOT/schemas/001_initial_schema.sql"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE"
  echo "Create it from docker/.env.example before applying the schema."
  exit 1
fi

if [ ! -f "$SCHEMA_FILE" ]; then
  echo "Missing $SCHEMA_FILE"
  exit 1
fi

DOCKER_BIN="${DOCKER_BIN:-docker}"
if ! command -v "$DOCKER_BIN" >/dev/null 2>&1; then
  if [ -x /usr/local/bin/docker ]; then
    DOCKER_BIN=/usr/local/bin/docker
  elif [ -x /Applications/Docker.app/Contents/Resources/bin/docker ]; then
    DOCKER_BIN=/Applications/Docker.app/Contents/Resources/bin/docker
  else
    echo "Docker CLI was not found. Start Docker Desktop and try again."
    exit 1
  fi
fi

read_env_value() {
  local key="$1"
  grep "^${key}=" "$ENV_FILE" | head -n 1 | cut -d '=' -f2-
}

POSTGRES_USER="$(read_env_value POSTGRES_USER)"
POSTGRES_PASSWORD="$(read_env_value POSTGRES_PASSWORD)"
POSTGRES_DB="$(read_env_value POSTGRES_DB)"

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
  echo "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in $ENV_FILE"
  exit 1
fi

echo "Applying schema to database: $POSTGRES_DB"

"$DOCKER_BIN" exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" realdeal-postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
  < "$SCHEMA_FILE"

echo "Schema apply completed."
