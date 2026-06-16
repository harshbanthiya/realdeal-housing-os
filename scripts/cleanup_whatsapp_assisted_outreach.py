#!/usr/bin/env python3
"""Phase 8.0 — Reversible teardown of assisted-outreach workspace data. Dry-run by default.

Deletes rows created by this phase so the workspace can be rebuilt: whatsapp_assisted_queue,
contact_sequence_enrollments, outreach_tracked_links, outreach_sequence_steps,
outreach_sequences, and (only with --include-events) contact_activity_events rows whose source
is 'cockpit_assisted' / 'manual_mark' / 'web_tracker'.

By default it does NOT touch channel_permissions or outreach_suppression_list — real opt-in /
opt-out consent decisions are preserved. Pass --include-consent to also remove the
assisted-sourced channel_permissions / suppression rows (use only to reset a test).

Counts only. Deleting requires BOTH --real-ok and --apply.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"


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


def counts_sql(include_events: bool, include_consent: bool) -> str:
    rows = [
        ("whatsapp_assisted_queue", "SELECT count(*) FROM whatsapp_assisted_queue"),
        ("contact_sequence_enrollments", "SELECT count(*) FROM contact_sequence_enrollments"),
        ("outreach_tracked_links", "SELECT count(*) FROM outreach_tracked_links"),
        ("outreach_sequence_steps", "SELECT count(*) FROM outreach_sequence_steps"),
        ("outreach_sequences", "SELECT count(*) FROM outreach_sequences"),
    ]
    if include_events:
        rows.append(("contact_activity_events(assisted)",
                     "SELECT count(*) FROM contact_activity_events WHERE source IN ('cockpit_assisted','manual_mark','web_tracker')"))
    if include_consent:
        rows.append(("channel_permissions(assisted)",
                     "SELECT count(*) FROM channel_permissions WHERE consent_source='assisted_whatsapp_reply'"))
        rows.append(("outreach_suppression_list(assisted)",
                     "SELECT count(*) FROM outreach_suppression_list WHERE reason='opted_out_via_assisted_whatsapp'"))
    return " UNION ALL ".join(f"SELECT '{name}' AS t, ({q})::text AS n" for name, q in rows) + " ORDER BY t;"


def delete_sql(include_events: bool, include_consent: bool) -> str:
    stmts = [
        "DELETE FROM whatsapp_assisted_queue;",
        "DELETE FROM contact_sequence_enrollments;",
        "DELETE FROM outreach_tracked_links;",
        "DELETE FROM outreach_sequence_steps;",
        "DELETE FROM outreach_sequences;",
    ]
    if include_events:
        stmts.append("DELETE FROM contact_activity_events WHERE source IN ('cockpit_assisted','manual_mark','web_tracker');")
    if include_consent:
        stmts.append("DELETE FROM channel_permissions WHERE consent_source='assisted_whatsapp_reply';")
        stmts.append("DELETE FROM outreach_suppression_list WHERE reason='opted_out_via_assisted_whatsapp';")
    guard = ("DO $$ DECLARE se text; BEGIN SELECT setting_value INTO se FROM outreach_settings "
             "WHERE setting_key='send_enabled'; IF se='true' THEN "
             "RAISE EXCEPTION 'Refusing: send_enabled must stay false.'; END IF; END $$;")
    return "BEGIN;\n" + "\n".join(stmts) + "\n" + guard + "\nCOMMIT;\nSELECT 'cleanup committed';"


def main() -> int:
    parser = argparse.ArgumentParser(description="Reversible teardown of assisted-outreach data. Dry-run by default.")
    parser.add_argument("--include-events", action="store_true",
                        help="Also delete assisted-sourced contact_activity_events rows.")
    parser.add_argument("--include-consent", action="store_true",
                        help="Also delete assisted-sourced channel_permissions / suppression rows (test reset only).")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print("Cleanup assisted-outreach workspace. Current row counts:")
    code, out = run_psql(counts_sql(args.include_events, args.include_consent))
    print(out if code == 0 else f"(count query failed) {out}")
    if not args.include_consent:
        print("NOTE: channel_permissions and outreach_suppression_list are PRESERVED (real consent).")

    if not (args.apply and args.real_ok):
        print("\nDry run only. No rows were deleted.")
        print("Deleting requires BOTH --real-ok and --apply.")
        return 0

    code, out = run_psql(delete_sql(args.include_events, args.include_consent))
    print("\nCleanup done:" if code == 0 else "Cleanup FAILED (rolled back):")
    print(out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
