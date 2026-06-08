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

# Phase 3.9C: the live Postgres cluster now lives on an APFS sparsebundle, not
# the exFAT data/postgres bind mount. APFS stores xattrs natively, so no
# AppleDouble ._* sidecars are generated under the data dir and the old
# preflight-clean/retry workaround is no longer load-bearing for Postgres.
SPARSEBUNDLE='/Volumes/RDH 5TB/rdh-postgres-data.sparsebundle'
APFS_VOLUME='/Volumes/RDH_POSTGRES_DATA'
APFS_PG_DIR="$APFS_VOLUME/postgres"

# Count macOS metadata junk (.DS_Store and AppleDouble ._*) under a directory, files only.
junk_count() {
  find "$1" -type f \( -name '.DS_Store' -o -name '._*' \) 2>/dev/null | wc -l | tr -d ' '
}

# Remove macOS metadata junk from the project tree. This still protects the rest
# of the repo (and the preserved data/postgres rollback copy); the live Postgres
# data dir is now on APFS (see ensure_apfs_postgres) and no longer depends on it.
preflight_clean() {
  if [ -x "$CLEANER" ]; then
    "$CLEANER" --apply
  else
    echo "Cleanup helper missing; running inline AppleDouble cleanup."
    echo "macOS metadata junk before: $(junk_count "$PROJECT_ROOT")"
    find "$PROJECT_ROOT" -type f \( -name '.DS_Store' -o -name '._*' \) ! -path "$DOCKER_DIR/.env" -delete 2>/dev/null || true
    echo "macOS metadata junk after: $(junk_count "$PROJECT_ROOT")"
  fi
}

# Ensure the APFS sparsebundle holding the live Postgres cluster is mounted and
# populated BEFORE Docker starts. Critical safety: if the volume is missing or
# empty, Docker would bind-mount an empty dir and Postgres would initialise a
# brand-new empty cluster (silent apparent data loss). Abort instead.
ensure_apfs_postgres() {
  if ! mount | grep -qF " on $APFS_VOLUME "; then
    echo "APFS Postgres volume not mounted; attaching sparsebundle..."
    if [ ! -e "$SPARSEBUNDLE" ]; then
      echo "ERROR: sparsebundle missing: $SPARSEBUNDLE" >&2
      echo "Cannot start Postgres without its APFS data volume. Aborting." >&2
      exit 1
    fi
    hdiutil attach "$SPARSEBUNDLE" >/dev/null || {
      echo "ERROR: failed to attach sparsebundle $SPARSEBUNDLE" >&2
      exit 1
    }
  fi

  if [ ! -d "$APFS_PG_DIR" ]; then
    echo "ERROR: $APFS_PG_DIR is missing after mount; aborting before docker compose up." >&2
    exit 1
  fi
  if [ -z "$(ls -A "$APFS_PG_DIR" 2>/dev/null)" ]; then
    echo "ERROR: $APFS_PG_DIR is empty; refusing to start so Postgres cannot" >&2
    echo "initialise a fresh empty cluster over your data. Aborting." >&2
    exit 1
  fi
  if [ ! -f "$APFS_PG_DIR/PG_VERSION" ]; then
    echo "ERROR: $APFS_PG_DIR/PG_VERSION not found; this is not a valid Postgres" >&2
    echo "cluster directory. Aborting before docker compose up." >&2
    exit 1
  fi
  echo "APFS Postgres volume ready: $APFS_PG_DIR (cluster version $(cat "$APFS_PG_DIR/PG_VERSION"))."
}

# Mount + validate the APFS data volume before any docker compose call.
ensure_apfs_postgres

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
