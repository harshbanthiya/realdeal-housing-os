#!/usr/bin/env bash
# Fails the build if anything in public/ ships heavier than 2MB.
# Fix with: scripts/optimize-media.sh <file>
big=$(find public -type f -size +2M 2>/dev/null)
if [ -n "$big" ]; then
  echo "❌ Oversized assets in public/ (>2MB) — run scripts/optimize-media.sh on:" >&2
  echo "$big" >&2
  exit 1
fi
echo "✅ public/ media check passed (all files ≤2MB)"
