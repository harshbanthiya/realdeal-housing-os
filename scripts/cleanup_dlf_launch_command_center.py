#!/usr/bin/env python3
"""Phase 7.0 cleanup: remove ONLY the DLF launch command center seed rows (tagged phase=7.0).

Deletes rows seeded by seed_dlf_launch_command_center.py — the launch_projects row + its
launch_channels / launch_campaign_calendar / launch_lead_segments / launch_operator_tasks /
launch_readiness_checks, plus the phase-7.0-tagged campaign_drafts and ai_agent_tasks
placeholders. It NEVER deletes contacts, inbound leads, RERA rows, or building rows.

Safety: REFUSES if any tagged row has send_enabled=true or publish_enabled=true, any calendar/
campaign status is 'sent'/'published', or any tag carries communication_sent=true (i.e. real
outreach has begun). Dry-run by default; requires BOTH --apply and --real-ok. Prints counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, scalar, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.0"
SOURCE = "dlf_launch_command_center_seed"

# table -> jsonb tag column (ai_agent_tasks uses raw_input; everything else raw_context).
TAG_COL = {
    "launch_channels": "raw_context",
    "launch_campaign_calendar": "raw_context",
    "launch_lead_segments": "raw_context",
    "launch_operator_tasks": "raw_context",
    "launch_readiness_checks": "raw_context",
    "launch_projects": "raw_context",
    "campaign_drafts": "raw_context",
    "ai_agent_tasks": "raw_input",
}
# Child-first delete order (launch_* children, then launch_projects, then shared tables).
DELETE_ORDER = [
    "launch_channels", "launch_campaign_calendar", "launch_lead_segments",
    "launch_operator_tasks", "launch_readiness_checks", "launch_projects",
    "campaign_drafts", "ai_agent_tasks",
]
def tag_where(table: str, launch_key: str | None) -> str:
    col = TAG_COL[table]
    w = f"{col}->>'phase' = '{PHASE}' AND {col}->>'source' = '{SOURCE}'"
    # Scope shared tables by launch_key tag; scope launch_* by project's launch_key.
    if launch_key:
        if table in ("campaign_drafts", "ai_agent_tasks"):
            w += f" AND {col}->>'launch_key' = {sql_literal(launch_key)}"
        elif table == "launch_projects":
            w += f" AND launch_key = {sql_literal(launch_key)}"
        else:
            w += (f" AND launch_project_id IN (SELECT id FROM launch_projects "
                  f"WHERE launch_key = {sql_literal(launch_key)})")
    return w

def main() -> int:
    ap = argparse.ArgumentParser(description="Cleanup Phase 7.0 DLF launch command center seed rows.")
    ap.add_argument("--launch-key", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    args = ap.parse_args()

    launch_key = args.launch_key or None

    # ----- safety refusals (only over tagged rows) -----
    send_on = 0
    pub_on = 0
    for t in ("launch_channels", "launch_campaign_calendar", "campaign_drafts"):
        send_on += scalar(f"SELECT count(*) FROM {t} WHERE {tag_where(t, launch_key)} AND send_enabled = true;")
    for t in ("launch_channels", "launch_campaign_calendar"):
        pub_on += scalar(f"SELECT count(*) FROM {t} WHERE {tag_where(t, launch_key)} AND publish_enabled = true;")
    status_live = (
        scalar(f"SELECT count(*) FROM launch_campaign_calendar WHERE {tag_where('launch_campaign_calendar', launch_key)} AND status IN ('sent','published');")
        + scalar(f"SELECT count(*) FROM campaign_drafts WHERE {tag_where('campaign_drafts', launch_key)} AND status IN ('sent','published');"))
    comm_sent = 0
    for t, col in TAG_COL.items():
        comm_sent += scalar(f"SELECT count(*) FROM {t} WHERE {tag_where(t, launch_key)} AND {col}->>'communication_sent' = 'true';")

    if send_on:
        print(f"Refusing: {send_on} tagged row(s) have send_enabled=true. Not deleting.")
        return 1
    if pub_on:
        print(f"Refusing: {pub_on} tagged row(s) have publish_enabled=true. Not deleting.")
        return 1
    if status_live:
        print(f"Refusing: {status_live} tagged row(s) are sent/published. Not deleting.")
        return 1
    if comm_sent:
        print(f"Refusing: {comm_sent} tagged row(s) marked communication_sent=true. Not deleting.")
        return 1

    # ----- counts -----
    print(f"=== Phase 7.0 DLF launch cleanup [{'APPLY' if (args.apply and args.real_ok) else 'DRY-RUN'}] ===")
    print(f"launch_key={launch_key or '(all phase-7.0)'}")
    print("(only rows tagged phase=7.0/source=dlf_launch_command_center_seed; "
          "contacts/leads/RERA/building rows untouched)")
    total = 0
    for t in DELETE_ORDER:
        n = scalar(f"SELECT count(*) FROM {t} WHERE {tag_where(t, launch_key)};")
        total += n
        print(f"  {t}: {n}")
    print(f"total_rows_in_scope={total}")

    if not (args.apply and args.real_ok):
        print("DRY-RUN only: nothing deleted. Re-run with --apply --real-ok to delete.")
        return 0

    sql = ["BEGIN;"]
    for t in DELETE_ORDER:
        sql.append(f"DELETE FROM {t} WHERE {tag_where(t, launch_key)};")
    sql.append("COMMIT;")
    code, out = run_psql("\n".join(sql))
    if code != 0:
        print(f"Delete FAILED (rolled back): {out[:300]}")
        return 2
    print(f"DELETED {total} tagged Phase 7.0 row(s). No contacts/leads/RERA/building rows touched.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
