#!/usr/bin/env bash
# Phase 3.9B planning helper. INFORMATIONAL ONLY — makes NO changes.
#
# Prints the current Postgres storage setup, feasibility checks, and the proposed
# APFS-sparsebundle migration target (Option B). It never creates the disk image,
# never moves data, never writes to the database, and never prints secrets.
#
# See docs/POSTGRES_STORAGE_MIGRATION_PLAN.md for the full plan.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/docker/.env"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.yml"

# Proposed Option B targets (NOT created by this script).
SPARSEBUNDLE='/Volumes/RDH 5TB/rdh-postgres-data.sparsebundle'
MOUNT_POINT='/Volumes/RDH_POSTGRES_DATA'
PG_TARGET="$MOUNT_POINT/postgres"

read_env_value() {
  [ -f "$ENV_FILE" ] || { echo ""; return; }
  grep "^$1=" "$ENV_FILE" | head -n1 | cut -d= -f2-
}

echo "=== Postgres storage migration PLAN (informational; no changes made) ==="
echo

echo "--- Current bind mapping (from docker-compose.yml) ---"
grep -nE 'postgresql/data' "$COMPOSE_FILE" | sed 's/^/  /' || echo "  (mapping not found)"
echo

echo "--- Current data/postgres size ---"
if [ -d "$PROJECT_ROOT/data/postgres" ]; then
  du -sh "$PROJECT_ROOT/data/postgres" 2>/dev/null | sed 's/^/  /'
  echo "  AppleDouble junk files under data/postgres: $(find "$PROJECT_ROOT/data/postgres" -type f \( -name '._*' -o -name '.DS_Store' \) 2>/dev/null | wc -l | tr -d ' ')"
else
  echo "  (data/postgres not present)"
fi
echo

echo "--- Feasibility checks (Option B: APFS sparsebundle) ---"
echo "  macOS: $(sw_vers -productVersion 2>/dev/null || echo unknown)"
command -v hdiutil >/dev/null 2>&1 && echo "  hdiutil: available" || echo "  hdiutil: MISSING"
echo "  free space on drive:"; df -h '/Volumes/RDH 5TB' 2>/dev/null | sed 's/^/    /'
echo "  Spotlight on volume:"; mdutil -s '/Volumes/RDH 5TB' 2>/dev/null | tail -1 | sed 's/^/    /'
echo

echo "--- Database sizes (counts/sizes only; no secrets, no contact data) ---"
USER_NAME="$(read_env_value POSTGRES_USER)"
PASSWORD="$(read_env_value POSTGRES_PASSWORD)"
if [ -n "$USER_NAME" ] && [ -n "$PASSWORD" ] && docker ps --format '{{.Names}}' | grep -q '^realdeal-postgres$'; then
  docker exec -i -e PGPASSWORD="$PASSWORD" realdeal-postgres \
    psql -U "$USER_NAME" -d postgres -At -F'|' \
    -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database WHERE datistemplate=false ORDER BY datname;" \
    2>/dev/null | sed 's/^/  /' || echo "  (could not query database)"
else
  echo "  (postgres container not running or env missing; skipping DB sizes)"
fi
echo

echo "--- Proposed Option B target (NOT created) ---"
echo "  sparsebundle : $SPARSEBUNDLE"
echo "  mount point  : $MOUNT_POINT"
echo "  postgres path: $PG_TARGET"
echo "  mounted now? : $([ -d "$PG_TARGET" ] && echo yes || echo no)"
echo
echo "This script made NO changes. To proceed, follow docs/POSTGRES_STORAGE_MIGRATION_PLAN.md"
echo "after explicit approval, and back up first with backup_postgres_before_migration.sh --apply."
