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

CLEANER="$PROJECT_ROOT/scripts/clean_appledouble_junk.sh"
PG_DATA_DIR="$PROJECT_ROOT/data/postgres"

# Count macOS metadata junk (.DS_Store and AppleDouble ._*) under a directory, files only.
junk_count() {
  find "$1" -type f \( -name '.DS_Store' -o -name '._*' \) 2>/dev/null | wc -l | tr -d ' '
}

# Remove macOS metadata junk from the whole project tree, then refuse to continue
# if any remain under the Postgres data dir. On external / exFAT volumes these
# files break the Postgres container's entrypoint permission pass.
preflight_clean() {
  if [ -x "$CLEANER" ]; then
    "$CLEANER" --apply
  else
    echo "Cleanup helper missing; running inline AppleDouble cleanup."
    echo "macOS metadata junk before: $(junk_count "$PROJECT_ROOT")"
    find "$PROJECT_ROOT" -type f \( -name '.DS_Store' -o -name '._*' \) ! -path "$DOCKER_DIR/.env" -delete 2>/dev/null || true
    echo "macOS metadata junk after: $(junk_count "$PROJECT_ROOT")"
  fi

  if [ -d "$PG_DATA_DIR" ]; then
    pg_junk="$(junk_count "$PG_DATA_DIR")"
    echo "macOS metadata junk under data/postgres: $pg_junk"
    if [ "$pg_junk" != "0" ]; then
      echo "ERROR: $pg_junk macOS metadata junk file(s) remain under data/postgres after cleanup." >&2
      echo "Postgres would fail its entrypoint permission pass; aborting before docker compose up." >&2
      echo "Confirm Spotlight indexing is off for this volume (mdutil -s), then re-run" >&2
      echo "./scripts/clean_appledouble_junk.sh --apply. See README.md (AppleDouble / exFAT)." >&2
      exit 1
    fi
  fi
}

cd "$DOCKER_DIR"

# Stage the bring-up: start Postgres first and wait until it is healthy before
# launching the rest of the stack. On exFAT/external volumes Docker can
# re-materialise AppleDouble junk during a multi-container bring-up and race the
# Postgres entrypoint, so each attempt re-cleans from a stopped Postgres.
ATTEMPT=1
MAX_ATTEMPTS=3
while : ; do
  docker compose --env-file .env rm -sf postgres >/dev/null 2>&1 || true
  preflight_clean
  echo "Starting Postgres (attempt $ATTEMPT of $MAX_ATTEMPTS)..."
  if docker compose --env-file .env up -d --wait --wait-timeout 90 postgres; then
    break
  fi
  if [ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]; then
    echo "ERROR: Postgres did not become healthy after $MAX_ATTEMPTS attempts." >&2
    echo "This is usually exFAT AppleDouble junk regenerating under data/postgres." >&2
    echo "See README.md (AppleDouble / exFAT) for durable fix options." >&2
    exit 1
  fi
  echo "Postgres unhealthy; recreating and retrying after re-clean..."
  ATTEMPT=$((ATTEMPT + 1))
done

# Postgres is healthy: bring up the rest of the stack.
docker compose --env-file .env up -d
docker compose --env-file .env ps
