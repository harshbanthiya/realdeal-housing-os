#!/usr/bin/env python3
"""Phase 8.0 — WhatsApp assisted-outreach + activity-timeline summary (READ-ONLY).

Prints counts only (masked names never shown in full): settings/gate, sequence state,
today's owner queue, daily send budget, engagement tiers, eligible-owner funnel, and the
top of the activity timeline. Makes NO writes and never sends anything.
"""

from __future__ import annotations

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


def section(title: str, sql: str) -> None:
    print(f"\n== {title} ==")
    code, out = run_psql(sql)
    if code != 0:
        print(f"  (query failed) {out}")
        return
    print(out if out else "  (no rows)")


def main() -> int:
    print("WhatsApp assisted outreach summary (read-only, counts only).")

    section("settings / gate", """
        SELECT setting_key || ' = ' || setting_value FROM outreach_settings ORDER BY setting_key;
    """)

    section("readiness gate (autosend must stay false)", """
        SELECT 'send_enabled='||send_enabled_setting
             ||'  active_sequences='||active_sequences
             ||'  pending_today='||pending_today
             ||'  whatsapp_permissions_allowed='||whatsapp_permissions_allowed
             ||'  optins_recorded='||optins_recorded
             ||'  autosend_enabled(should be f)='||autosend_enabled_should_be_false
        FROM vw_whatsapp_assisted_readiness;
    """)

    section("sequences", """
        SELECT s.status||'  '||s.name||'  ('||count(st.id)||' steps, owner_only='||s.owner_only||')'
        FROM outreach_sequences s
        LEFT JOIN outreach_sequence_steps st ON st.sequence_id = s.id
        GROUP BY s.id, s.status, s.name, s.owner_only ORDER BY s.created_at;
    """)

    section("daily send budget", """
        SELECT 'cap='||daily_cap||'  sent_today='||sent_today
             ||'  pending_today='||pending_today||'  remaining_today='||remaining_today
        FROM vw_outreach_daily_send_status;
    """)

    section("today's owner queue by status", """
        SELECT status||': '||count(*) FROM whatsapp_assisted_queue
        WHERE queued_for_date = CURRENT_DATE GROUP BY status ORDER BY status;
    """)

    section("engagement tiers (all touched contacts)", """
        SELECT engagement_tier||': '||count(*)
             ||(CASE WHEN bool_or(do_not_spam_flag) THEN '  (some flagged do_not_spam)' ELSE '' END)
        FROM vw_contact_engagement_score GROUP BY engagement_tier ORDER BY 1;
    """)

    section("owner outreach funnel", """
        SELECT 'eligible_owners='||count(*)
             ||'  with_number='||count(*) FILTER (WHERE has_number)
             ||'  suppressed='||count(*) FILTER (WHERE is_suppressed)
             ||'  opted_out='||count(*) FILTER (WHERE is_opted_out)
             ||'  in_cooldown='||count(*) FILTER (WHERE in_cooldown)
             ||'  ready_to_enroll='||count(*) FILTER (
                    WHERE has_number AND NOT is_suppressed AND NOT is_opted_out AND NOT in_cooldown)
        FROM vw_owner_outreach_eligibility;
    """)

    section("activity timeline (latest 10, masked)", """
        SELECT to_char(occurred_at,'YYYY-MM-DD HH24:MI')||'  '||contact_masked
             ||'  '||channel||'/'||event_type||' ('||direction||')'
        FROM vw_contact_activity_timeline LIMIT 10;
    """)

    print("\nDone. No writes were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
