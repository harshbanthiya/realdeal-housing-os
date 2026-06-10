#!/usr/bin/env python3
"""Phase 7.1 cleanup: remove ONLY the DLF launch funnel workspace seed rows (tagged phase=7.1).

Deletes rows seeded by seed_dlf_launch_funnel_workspace.py — the funnel review items, landing-page
spec, lead-capture form, UTM specs, content pillars, message templates, social drafts, lead-scoring
rules, and the 2 phase-7.1 readiness checks. It NEVER deletes contacts, inbound leads, RERA rows,
the launch_projects row, launch_channels, or any Phase 7.0 rows.

Safety: REFUSES if any tagged row has send_enabled=true or publish_enabled=true, any draft status
is sent/published/scheduled, or any tag carries communication_sent=true. Dry-run by default;
requires BOTH --apply and --real-ok. Prints counts only.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.1"
SOURCE = "dlf_launch_funnel_workspace_seed"
TAG_WHERE = f"raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}'"

# Child (review items) first, then draft tables, then the phase-7.1 readiness checks.
DELETE_ORDER = [
    "launch_draft_review_items",
    "launch_landing_page_specs",
    "launch_lead_capture_forms",
    "launch_utm_campaign_specs",
    "launch_content_pillars",
    "launch_message_templates",
    "launch_social_content_drafts",
    "launch_lead_scoring_rules",
    "launch_readiness_checks",
]


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def sql_literal(value) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


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
    return result.returncode, (result.stdout.strip() or result.stderr.strip())


def scalar(sql: str) -> int:
    code, out = run_psql(sql)
    if code != 0 or not out:
        return 0
    try:
        return int(out.splitlines()[0])
    except ValueError:
        return 0


def where(table: str, launch_key: str | None) -> str:
    w = TAG_WHERE
    if launch_key:
        w += (f" AND launch_project_id IN (SELECT id FROM launch_projects "
              f"WHERE launch_key = {sql_literal(launch_key)})")
    return w


def main() -> int:
    ap = argparse.ArgumentParser(description="Cleanup Phase 7.1 DLF launch funnel workspace seed rows.")
    ap.add_argument("--launch-key", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    args = ap.parse_args()

    launch_key = args.launch_key or None

    # ----- safety refusals (only over tagged rows) -----
    send_on = scalar(f"SELECT count(*) FROM launch_message_templates WHERE {where('launch_message_templates', launch_key)} AND send_enabled = true;")
    pub_on = 0
    for t in ("launch_landing_page_specs", "launch_lead_capture_forms", "launch_social_content_drafts"):
        pub_on += scalar(f"SELECT count(*) FROM {t} WHERE {where(t, launch_key)} AND publish_enabled = true;")
    status_live = scalar(
        f"SELECT count(*) FROM launch_social_content_drafts WHERE {where('launch_social_content_drafts', launch_key)} "
        "AND draft_status IN ('sent','published','scheduled');")
    comm_sent = 0
    for t in DELETE_ORDER:
        comm_sent += scalar(f"SELECT count(*) FROM {t} WHERE {where(t, launch_key)} AND raw_context->>'communication_sent' = 'true';")

    if send_on:
        print(f"Refusing: {send_on} tagged message template(s) have send_enabled=true. Not deleting.")
        return 1
    if pub_on:
        print(f"Refusing: {pub_on} tagged row(s) have publish_enabled=true. Not deleting.")
        return 1
    if status_live:
        print(f"Refusing: {status_live} tagged draft(s) are sent/published/scheduled. Not deleting.")
        return 1
    if comm_sent:
        print(f"Refusing: {comm_sent} tagged row(s) marked communication_sent=true. Not deleting.")
        return 1

    # ----- counts -----
    print(f"=== Phase 7.1 DLF funnel workspace cleanup [{'APPLY' if (args.apply and args.real_ok) else 'DRY-RUN'}] ===")
    print(f"launch_key={launch_key or '(all phase-7.1)'}")
    print("(only rows tagged phase=7.1/source=dlf_launch_funnel_workspace_seed; "
          "contacts/leads/RERA/launch_project/launch_channels/Phase-7.0 rows untouched)")
    total = 0
    for t in DELETE_ORDER:
        n = scalar(f"SELECT count(*) FROM {t} WHERE {where(t, launch_key)};")
        total += n
        print(f"  {t}: {n}")
    print(f"total_rows_in_scope={total}")

    if not (args.apply and args.real_ok):
        print("DRY-RUN only: nothing deleted. Re-run with --apply --real-ok to delete.")
        return 0

    sql = ["BEGIN;"]
    for t in DELETE_ORDER:
        sql.append(f"DELETE FROM {t} WHERE {where(t, launch_key)};")
    sql.append("COMMIT;")
    code, out = run_psql("\n".join(sql))
    if code != 0:
        print(f"Delete FAILED (rolled back): {out[:300]}")
        return 2
    print(f"DELETED {total} tagged Phase 7.1 row(s). No contacts/leads/RERA/launch_project/"
          "launch_channels/Phase-7.0 rows touched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
