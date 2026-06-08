#!/usr/bin/env bash
# Phase 3.9B pre-migration backup. DRY-RUN BY DEFAULT.
#
# Default (no flag): prints what would be backed up and where. Makes NO changes.
# With --apply: writes a logical pg_dumpall of all databases to backups/ (git-ignored).
#
# Safety:
#   - Never deletes or moves any database data.
#   - Never prints secrets (PGPASSWORD is passed to the container, never echoed).
#   - The dump is written to a file, not stdout, so no contact data is printed.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/docker/.env"
APPLY=false

case "${1:-}" in
  "") ;;
  --apply) APPLY=true ;;
  *) echo "Usage: $0 [--apply]" >&2; exit 1 ;;
esac

read_env_value() {
  [ -f "$ENV_FILE" ] || { echo ""; return; }
  grep "^$1=" "$ENV_FILE" | head -n1 | cut -d= -f2-
}

USER_NAME="$(read_env_value POSTGRES_USER)"
PASSWORD="$(read_env_value POSTGRES_PASSWORD)"
if [ -z "$USER_NAME" ] || [ -z "$PASSWORD" ]; then
  echo "Missing POSTGRES_USER / POSTGRES_PASSWORD in docker/.env." >&2
  exit 1
fi
if ! docker ps --format '{{.Names}}' | grep -q '^realdeal-postgres$'; then
  echo "realdeal-postgres is not running. Start the stack first (./start.sh)." >&2
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$PROJECT_ROOT/backups/postgres_pre_migration_$STAMP"
DUMP_FILE="$BACKUP_DIR/all_databases.sql"

echo "Pre-migration Postgres backup (logical pg_dumpall)."
echo "  databases on server:"
docker exec -i -e PGPASSWORD="$PASSWORD" realdeal-postgres \
  psql -U "$USER_NAME" -d postgres -At \
  -c "SELECT datname FROM pg_database WHERE datistemplate=false ORDER BY datname;" \
  2>/dev/null | sed 's/^/    /'
echo "  target file: $DUMP_FILE  (backups/ is git-ignored)"
echo "  source data/postgres size: $(du -sh "$PROJECT_ROOT/data/postgres" 2>/dev/null | cut -f1)"

if [ "$APPLY" = false ]; then
  echo "Dry run only. Re-run with --apply to write the backup. No changes made."
  exit 0
fi

mkdir -p "$BACKUP_DIR"
echo "Writing pg_dumpall to backup file..."
docker exec -i -e PGPASSWORD="$PASSWORD" realdeal-postgres \
  pg_dumpall -U "$USER_NAME" --clean --if-exists > "$DUMP_FILE"
echo "Backup written: $DUMP_FILE"
echo "  size: $(du -sh "$DUMP_FILE" 2>/dev/null | cut -f1)"
echo "No database data was deleted or moved."
