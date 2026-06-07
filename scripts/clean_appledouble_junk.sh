#!/usr/bin/env bash
# Remove macOS metadata junk from the project tree.
#
# macOS on external / exFAT volumes creates ".DS_Store" and AppleDouble "._*"
# sidecar files. Inside data/postgres these break the Postgres container's
# entrypoint permission pass and make the database fail to start.
#
# Dry-run by default; pass --apply to actually delete.
#
# Safety:
#   - Deletes regular FILES only, never directories.
#   - Only matches ".DS_Store" and files whose basename starts with "._".
#   - Never touches docker/.env (or any other non-junk file).
#   - Prints COUNTS only, never file paths, so real source filenames embedded
#     in "._<name>" sidecars are not exposed.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY=false

case "${1:-}" in
  "") ;;
  --apply) APPLY=true ;;
  *) echo "Usage: $0 [--apply]" >&2; exit 1 ;;
esac

echo "Only removes macOS metadata junk files. This does not repair database corruption."

# Count regular junk files (.DS_Store or basename starting with ._), excluding docker/.env.
count_junk() {
  find "$PROJECT_ROOT" -type f \( -name '.DS_Store' -o -name '._*' \) \
    ! -path "$PROJECT_ROOT/docker/.env" 2>/dev/null | wc -l | tr -d ' '
}

BEFORE="$(count_junk)"
echo "macOS metadata junk files found: $BEFORE"

if [ "$APPLY" = false ]; then
  echo "Dry run only. Re-run with --apply to delete matching files. No files were changed."
  exit 0
fi

echo "Apply mode: deleting macOS metadata junk files (files only, never directories)."
find "$PROJECT_ROOT" -type f \( -name '.DS_Store' -o -name '._*' \) \
  ! -path "$PROJECT_ROOT/docker/.env" -delete 2>/dev/null || true

AFTER="$(count_junk)"
DELETED=$(( BEFORE - AFTER ))
echo "Deleted: $DELETED. Remaining: $AFTER."
