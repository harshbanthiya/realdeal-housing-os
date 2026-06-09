#!/usr/bin/env python3
"""Human dashboard summary for NocoDB operators. Read-only; counts only; no DB writes.

Prints, for a human about to operate the NocoDB dashboard:
  * NocoDB setup status (best-effort, detected via docker)
  * key dashboard view row counts
  * active owner relationships
  * pending owner/unit candidates
  * duplicate risks
  * revert-ready active relationships
  * the single next recommended manual action

Never prints person names, phones, emails, websites, or addresses. Building/unit
names are business data and may appear in the underlying views, but this script
prints counts and a recommended-action label only.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
NOCODB_CONTAINER = "realdeal-nocodb"
POSTGRES_CONTAINER = "realdeal-postgres"


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
    db_name = read_env_value("POSTGRES_DB") or "realdeal_os"
    if not user or not password:
        return 1, "Missing POSTGRES_USER or POSTGRES_PASSWORD in docker/.env."
    command = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        POSTGRES_CONTAINER, "psql", "-U", user, "-d", db_name,
        "-v", "ON_ERROR_STOP=1", "-At", "-F", "|",
    ]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


def nocodb_status() -> list[str]:
    """Best-effort NocoDB readiness check. Never raises; degrades gracefully."""
    lines: list[str] = []
    try:
        running = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", NOCODB_CONTAINER],
            text=True, capture_output=True, check=False,
        )
        is_running = running.returncode == 0 and running.stdout.strip() == "true"
        lines.append(f"  container_running: {'yes' if is_running else 'no'}")
        if is_running:
            envcheck = subprocess.run(
                ["docker", "exec", NOCODB_CONTAINER, "printenv", "NC_ALLOW_LOCAL_EXTERNAL_DBS"],
                text=True, capture_output=True, check=False,
            )
            flag = envcheck.stdout.strip() if envcheck.returncode == 0 else ""
            allowed = flag.lower() == "true"
            lines.append(f"  allow_local_external_dbs: {flag or '(not set)'}"
                         f"  -> internal-host connection {'ENABLED' if allowed else 'BLOCKED'}")
            net = subprocess.run(
                ["docker", "exec", NOCODB_CONTAINER, "getent", "hosts", "postgres"],
                text=True, capture_output=True, check=False,
            )
            reachable = net.returncode == 0 and bool(net.stdout.strip())
            lines.append(f"  resolves_host 'postgres': {'yes' if reachable else 'no'}")
        lines.append("  ui_url: http://localhost:8080  (connect data source to host 'postgres', db 'realdeal_os')")
    except Exception as exc:  # docker missing / not permitted
        lines.append(f"  (NocoDB status undetectable: {exc})")
    return lines


COUNT_SQL = """
SELECT 'canonical_contacts', canonical_contacts FROM vw_human_dashboard_home
UNION ALL SELECT 'active_owner_relationships', active_owner_relationships FROM vw_human_dashboard_home
UNION ALL SELECT 'pending_candidate_queue', pending_candidate_queue FROM vw_human_dashboard_home
UNION ALL SELECT 'safe_candidate_queue', safe_candidate_queue FROM vw_human_dashboard_home
UNION ALL SELECT 'duplicate_risk_count', duplicate_risk_count FROM vw_human_dashboard_home
UNION ALL SELECT 'revert_ready_active_relationships', revert_ready_active_relationships FROM vw_human_dashboard_home
UNION ALL SELECT 'communications_sent', communications_sent FROM vw_human_dashboard_home
UNION ALL SELECT 'buildings', buildings FROM vw_human_dashboard_home
UNION ALL SELECT 'building_units', building_units FROM vw_human_dashboard_home;
"""

NEXT_ACTION_SQL = """
SELECT action_type, priority, count(*)
FROM vw_human_next_actions
GROUP BY action_type, priority
ORDER BY priority, action_type
LIMIT 1;
"""


def main() -> int:
    print("Human dashboard summary. Counts only; no raw personal values are printed.")
    print("")
    print("NocoDB setup status:")
    for line in nocodb_status():
        print(line)
    print("")

    print("Key dashboard counts (from vw_human_dashboard_home):")
    code, output = run_psql(COUNT_SQL)
    if code != 0:
        print(f"  ERROR querying database: {output}")
        return code
    for row in output.splitlines():
        if "|" in row:
            key, val = row.split("|", 1)
            print(f"  {key}: {val}")
    print("")

    print("Next recommended manual action (highest-priority group in vw_human_next_actions):")
    code2, action = run_psql(NEXT_ACTION_SQL)
    if code2 == 0 and "|" in action:
        action_type, priority, count = action.split("|")
        print(f"  {action_type} (priority {priority}); {count} item(s) in this group")
        print("  -> perform via the guarded terminal scripts; NocoDB is for inspection only.")
    else:
        print("  none / undetectable")
    return code or code2


if __name__ == "__main__":
    raise SystemExit(main())
