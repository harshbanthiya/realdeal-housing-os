#!/usr/bin/env python3
"""Print a count-only DLF operator cockpit summary.

Read-only helper for Phase 7.5. It queries cockpit/dashboard views and prints
counts/statuses only. It never writes to the database and never prints contact
names, phones, emails, addresses, raw copy bodies, or secrets.
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


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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


def print_query(title: str, sql: str) -> int:
    code, out = run_psql(sql)
    print(f"\n[{title}]")
    if code != 0:
        print(out)
        return code
    print(out if out else "(none)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Print DLF operator cockpit counts only.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    args = parser.parse_args()
    launch_key = sql_literal(args.launch_key)

    print("DLF operator cockpit summary. Counts/statuses only; no raw personal values.")
    print(f"launch_key={args.launch_key}")

    queries = [
        (
            "cockpit_home",
            f"""
SELECT concat_ws('|',
  'home',
  launch_status,
  ready_for_launch_push::text,
  ready_for_live_lead_capture::text,
  ready_for_campaign_selection::text,
  ready_to_build_n8n::text,
  ready_to_activate_n8n::text,
  send_enabled_count,
  publish_enabled_count,
  inbound_leads,
  pending_blockers,
  pending_high_priority_tasks,
  pending_reviews_total,
  next_required_action
)
FROM vw_dlf_operator_cockpit_home
WHERE launch_key = {launch_key};
""",
        ),
        (
            "top_blockers",
            f"""
SELECT 'readiness|' || priority || '|' || status || '|' || count(*)
FROM vw_dlf_operator_today_tasks
WHERE launch_key = {launch_key}
  AND item_type = 'readiness_check'
GROUP BY priority, status
ORDER BY priority, status;
""",
        ),
        (
            "today_high_priority_tasks",
            f"""
SELECT 'today_tasks|' || item_type || '|' || priority || '|' || status || '|' || count(*)
FROM vw_dlf_operator_today_tasks
WHERE launch_key = {launch_key}
GROUP BY item_type, priority, status
ORDER BY item_type, priority, status;
""",
        ),
        (
            "review_backlog_by_queue",
            f"""
SELECT 'review_backlog|' || source_queue || '|' || status || '|' || count(*)
FROM vw_dlf_operator_review_backlog
WHERE launch_key = {launch_key}
GROUP BY source_queue, status
ORDER BY source_queue, status;
""",
        ),
        (
            "calendar_next_14_days",
            f"""
SELECT 'calendar|' || channel || '|' || status || '|' || send_enabled::text || '|' || publish_enabled::text || '|' || count(*)
FROM vw_dlf_operator_campaign_calendar_next_14_days
WHERE launch_key = {launch_key}
GROUP BY channel, status, send_enabled, publish_enabled
ORDER BY channel, status, send_enabled, publish_enabled;
""",
        ),
        (
            "audience_readiness",
            f"""
SELECT concat_ws('|',
  'audience',
  total_candidates,
  approved_for_segment,
  pending_permission_review,
  whatsapp_allowed,
  email_allowed,
  suppressed,
  ready_for_campaign_selection::text
)
FROM vw_dlf_operator_audience_readiness
WHERE launch_key = {launch_key};
""",
        ),
        (
            "lead_intake_readiness",
            f"""
SELECT concat_ws('|',
  'lead_intake',
  endpoints_planned,
  endpoints_active,
  field_mappings,
  approved_field_mappings,
  attribution_rules,
  approved_attribution_rules,
  inbound_leads,
  external_call_allowed_count,
  ready_for_live_lead_capture::text
)
FROM vw_dlf_operator_lead_intake_readiness
WHERE launch_key = {launch_key};
""",
        ),
        (
            "n8n_readiness",
            f"""
SELECT concat_ws('|',
  'n8n',
  workflow_blueprints,
  workflows_approved_for_build,
  workflows_built,
  active_workflows,
  pending_reviews,
  external_call_allowed_count,
  ready_to_build_in_n8n::text,
  ready_to_activate::text
)
FROM vw_dlf_operator_n8n_readiness
WHERE launch_key = {launch_key};
""",
        ),
        (
            "content_readiness",
            f"""
SELECT concat_ws('|',
  'content',
  landing_pages,
  lead_forms,
  message_templates,
  social_drafts,
  content_pillars,
  draft_reviews_pending,
  approved_reviews,
  send_enabled_count,
  publish_enabled_count,
  ready_for_content_push::text
)
FROM vw_dlf_operator_content_readiness
WHERE launch_key = {launch_key};
""",
        ),
        (
            "safety_posture",
            f"""
SELECT concat_ws('|',
  'safety',
  send_enabled_count,
  publish_enabled_count,
  external_call_allowed_count,
  active_n8n_workflows,
  live_lead_capture_ready::text,
  contacts_approved_for_campaign,
  communication_sent,
  published_count,
  safety_status,
  safety_notes
)
FROM vw_dlf_operator_safety_posture
WHERE launch_key = {launch_key};
""",
        ),
    ]

    for title, sql in queries:
        code = print_query(title, sql)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
