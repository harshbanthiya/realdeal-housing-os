#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY=false

if [ "${1:-}" = "--apply" ]; then
  APPLY=true
elif [ "${1:-}" != "" ]; then
  echo "Usage: $0 [--apply]"
  exit 1
fi

echo "Only removes macOS metadata junk files. This does not repair database corruption."

if [ "$APPLY" = false ]; then
  echo "Dry run only. Re-run with --apply to delete matching files."
else
  echo "Apply mode: deleting matching macOS metadata junk files."
fi

find "$PROJECT_ROOT" -type f \( -name '.DS_Store' -o -name '._*' \) -print0 |
while IFS= read -r -d '' path; do
  basename="$(basename "$path")"

  if [ "$path" = "$PROJECT_ROOT/docker/.env" ]; then
    continue
  fi

  case "$basename" in
    .DS_Store|._*) ;;
    *) continue ;;
  esac

  printf '%s\n' "$path"
  if [ "$APPLY" = true ]; then
    rm -f -- "$path"
  fi
done
