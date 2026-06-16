#!/usr/bin/env python3
"""Phase 8.2 — Clear assisted-outreach queue entries. Dry-run by default.

Removes queued send tasks so the operator can rebuild a clean queue:

  --queue-id <uuid>   Remove ONE queue row (and its now-orphaned enrollment), so that
                      contact leaves outreach and can be re-queued later.
  --today             Clear ALL of today's queue rows (+ their orphaned enrollments).
  --pending-only      With --today, only clear rows still in 'pending' status.

It deletes ONLY whatsapp_assisted_queue rows and the contact_sequence_enrollments that
no longer have any queue row. It NEVER deletes contact_activity_events (the timeline /
sent history is preserved), NEVER touches channel_permissions or outreach_suppression_list
(real consent stays), and NEVER flips send_enabled. Because past 'sent' events remain, the
cooldown guard still protects a cleared contact from immediate re-queueing.

Writing requires BOTH --real-ok and --apply.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    command = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql", "-U", user, "-d", db_name,
        "-v", "ON_ERROR_STOP=1", "-At", "-F", "|",
    ]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


def where_clause(queue_id: str | None, pending_only: bool) -> str:
    if queue_id:
        return f"id = '{queue_id}'::uuid"
    clause = "queued_for_date = CURRENT_DATE"
    if pending_only:
        clause += " AND status = 'pending'"
    return clause


def probe_sql(where: str) -> str:
    return f"SELECT count(*) FROM whatsapp_assisted_queue WHERE {where};"


def clear_sql(where: str) -> str:
    # Capture affected enrollment ids FIRST (separate statement), then delete the queue
    # rows, then delete enrollments that are now orphaned. Done as distinct statements so
    # the final NOT EXISTS sees the post-delete state (a single WITH would see the old snapshot).
    return f"""
BEGIN;
CREATE TEMP TABLE _cleared_enr ON COMMIT DROP AS
  SELECT DISTINCT enrollment_id FROM whatsapp_assisted_queue
  WHERE {where} AND enrollment_id IS NOT NULL;
DELETE FROM whatsapp_assisted_queue WHERE {where};
DELETE FROM contact_sequence_enrollments e
WHERE e.id IN (SELECT enrollment_id FROM _cleared_enr)
  AND NOT EXISTS (SELECT 1 FROM whatsapp_assisted_queue q WHERE q.enrollment_id = e.id);
DO $$ DECLARE se text; BEGIN
  SELECT setting_value INTO se FROM outreach_settings WHERE setting_key='send_enabled';
  IF se='true' THEN RAISE EXCEPTION 'Refusing: send_enabled must stay false.'; END IF;
END $$;
COMMIT;
SELECT 'remaining_today='||count(*) FILTER (WHERE queued_for_date=CURRENT_DATE)
     ||'  remaining_total='||count(*) FROM whatsapp_assisted_queue;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear assisted-outreach queue entries. Dry-run by default.")
    parser.add_argument("--queue-id", default=None, help="Remove a single queue row by id.")
    parser.add_argument("--today", action="store_true", help="Clear all of today's queue rows.")
    parser.add_argument("--pending-only", action="store_true", help="With --today, only clear pending rows.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    if bool(args.queue_id) == bool(args.today):
        print("Refusing: pass exactly one of --queue-id <uuid> or --today.")
        return 2
    if args.queue_id and not UUID_RE.match(args.queue_id):
        print("Refusing: --queue-id must be a valid UUID.")
        return 2

    where = where_clause(args.queue_id, args.pending_only)
    target = f"queue id {args.queue_id}" if args.queue_id else ("today's pending rows" if args.pending_only else "today's queue")
    print(f"Clear outreach: {target}")

    code, out = run_psql(probe_sql(where))
    if code != 0:
        print(f"Probe failed: {out}")
        return code
    print(f"  would clear: {out} row(s) (+ orphaned enrollments; activity/consent preserved)")

    if not (args.apply and args.real_ok):
        print("\nDry run only. No rows were deleted.")
        print("Deleting requires BOTH --real-ok and --apply.")
        return 0

    code, out = run_psql(clear_sql(where))
    print("\nCleared:" if code == 0 else "Clear FAILED (rolled back):")
    print(out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
