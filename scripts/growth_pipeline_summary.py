#!/usr/bin/env python3
"""Phase 6.0 growth-pipeline summary. Read-only; counts only; no DB writes.

Prints status breakdowns for the growth/SEO/lead pipeline: SEO web profiles,
keyword statuses, content-brief statuses, publishing-queue statuses, inbound-lead
statuses, channel permissions, campaign drafts, AI-agent tasks, and the count of
send-enabled (communications-enabled) campaigns. Never prints person names, phones,
emails, websites, or addresses.
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


# (section label, table, status column). NULL statuses bucket as '(none)'.
SECTIONS = [
    ("seo_profiles", "building_web_profiles", "seo_status"),
    ("keywords", "seo_keywords", "status"),
    ("content_briefs", "content_briefs", "approval_status"),
    ("publishing_queue", "content_publishing_queue", "publish_status"),
    ("inbound_leads", "inbound_leads", "lead_status"),
    ("channel_permissions", "channel_permissions", "permission_status"),
    ("campaign_drafts", "campaign_drafts", "status"),
    ("ai_agent_tasks", "ai_agent_tasks", "status"),
]


def breakdown_sql() -> str:
    parts = [
        f"SELECT '{label}' AS section, COALESCE({col}::text, '(none)') AS bucket, count(*)::text AS n "
        f"FROM {table} GROUP BY 2"
        for label, table, col in SECTIONS
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY section, bucket;"


def main() -> int:
    print("Growth-pipeline summary. Counts only; no raw personal values are printed.")
    print("")

    code, output = run_psql(breakdown_sql())
    if code != 0:
        print(f"ERROR querying database: {output}")
        return code

    current = None
    for row in output.splitlines():
        if row.count("|") != 2:
            continue
        section, bucket, n = row.split("|")
        if section != current:
            print(f"{section}:")
            current = section
        print(f"  {bucket}: {n}")

    # Outreach posture (must be 0 in this phase).
    code2, enabled = run_psql(
        "SELECT count(*) FROM campaign_drafts WHERE send_enabled = true;"
    )
    print("")
    print("outreach posture:")
    print(f"  communications_enabled_count (send_enabled campaigns): {enabled if code2 == 0 else 'ERROR'}")
    print("  communications_sent_count: 0  (no send pipeline exists in this phase)")
    return code or code2


if __name__ == "__main__":
    raise SystemExit(main())
