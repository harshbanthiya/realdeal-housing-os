#!/bin/bash
# Run the daily workers if they haven't run today. TCC-free fallback to the
# launchd schedule — hooked into start.sh so any stack start guarantees a run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

LAST=$(python3 - <<EOF
import sys; sys.path.insert(0, "${ROOT}/scripts")
from _db import run_psql
print(run_psql("SELECT coalesce(max(started_at)::date::text,'') FROM worker_runs")[1])
EOF
)

if [ "$LAST" = "$(date +%F)" ]; then
  echo "Workers already ran today ($LAST) — skipping."
else
  echo "Running daily workers (last run: ${LAST:-never})..."
  python3 "$ROOT/workers/run_all.py"
fi
