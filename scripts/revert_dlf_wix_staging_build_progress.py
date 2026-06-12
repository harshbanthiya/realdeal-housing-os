#!/usr/bin/env python3
"""Phase 7.20 — revert the manual Wix staging build-progress changes. Dry-run by default.

Restores ONLY the rows advanced by record_dlf_wix_staging_build_progress.py, identified by the
`phase_7_20_action` marker in raw_context:

  * wix_staging_build_checklist_items -> checklist_status restored from phase_7_20_prev_status
  * wix_staging_qa_checks             -> qa_status restored from phase_7_20_prev_status
  * wix_staging_sites                 -> staging_status restored from phase_7_20_prev_status;
                                         staging_site_name/url cleared (they were set by Phase 7.20)

All Phase 7.20 markers are removed and the Phase 7.20 append-only action-log rows are deleted. It
never deletes the Phase 7.19 staging plan rows, never touches contacts/leads/messages, and refuses
if any staging site reports page_published, live_form_created, live_webhook_created,
real_domain_connected, public_indexing_enabled, or wix_api_call_made, or if any inbound lead exists.

Reverting requires BOTH --real-ok and --apply. Counts only.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.20"


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
    return result.returncode, result.stdout.strip() or result.stderr.strip()


def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk})
SELECT
  (SELECT count(*) FROM wix_staging_build_checklist_items c WHERE c.launch_project_id IN (SELECT id FROM proj) AND c.raw_context ? 'phase_7_20_action'),
  (SELECT count(*) FROM wix_staging_qa_checks q WHERE q.launch_project_id IN (SELECT id FROM proj) AND q.raw_context ? 'phase_7_20_action'),
  (SELECT count(*) FROM wix_staging_sites s WHERE s.launch_project_id IN (SELECT id FROM proj) AND s.raw_context ? 'phase_7_20_action'),
  (SELECT count(*) FROM wix_staging_build_action_log l WHERE l.launch_project_id IN (SELECT id FROM proj) AND l.raw_context->>'phase' = '{PHASE}'),
  (SELECT count(*) FROM wix_staging_sites s WHERE s.launch_project_id IN (SELECT id FROM proj)
     AND (s.page_published OR s.live_form_created OR s.live_webhook_created OR s.real_domain_connected OR s.public_indexing_enabled OR s.wix_api_call_made)),
  (SELECT count(*) FROM inbound_leads);
"""


def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;
DO $GUARD$
DECLARE live int; inbound int;
BEGIN
  SELECT count(*) INTO live FROM wix_staging_sites s JOIN launch_projects p ON p.id = s.launch_project_id
    WHERE p.launch_key = {lk}
      AND (s.page_published OR s.live_form_created OR s.live_webhook_created
        OR s.real_domain_connected OR s.public_indexing_enabled OR s.wix_api_call_made);
  SELECT count(*) INTO inbound FROM inbound_leads;
  IF live > 0 THEN RAISE EXCEPTION 'Refusing revert: a staging site has a live/domain/index/publish/api flag set (%).', live; END IF;
  IF inbound <> 0 THEN RAISE EXCEPTION 'Refusing revert: inbound lead count is % (must be 0).', inbound; END IF;
END $GUARD$;

UPDATE wix_staging_build_checklist_items c SET
  checklist_status = COALESCE(c.raw_context->>'phase_7_20_prev_status', c.checklist_status),
  raw_context = (c.raw_context - 'phase_7_20_action' - 'phase_7_20_prev_status'),
  updated_at = now()
FROM launch_projects p
WHERE p.id = c.launch_project_id AND p.launch_key = {lk} AND c.raw_context ? 'phase_7_20_action';

UPDATE wix_staging_qa_checks q SET
  qa_status = COALESCE(q.raw_context->>'phase_7_20_prev_status', q.qa_status),
  raw_context = (q.raw_context - 'phase_7_20_action' - 'phase_7_20_prev_status'),
  updated_at = now()
FROM launch_projects p
WHERE p.id = q.launch_project_id AND p.launch_key = {lk} AND q.raw_context ? 'phase_7_20_action';

UPDATE wix_staging_sites s SET
  staging_status = COALESCE(s.raw_context->>'phase_7_20_prev_status', s.staging_status),
  staging_site_name = NULL,
  staging_site_url = NULL,
  raw_context = (s.raw_context - 'phase_7_20_action' - 'phase_7_20_prev_status'),
  updated_at = now()
FROM launch_projects p
WHERE p.id = s.launch_project_id AND p.launch_key = {lk} AND s.raw_context ? 'phase_7_20_action';

DELETE FROM wix_staging_build_action_log l
USING launch_projects p
WHERE l.launch_project_id = p.id AND p.launch_key = {lk} AND l.raw_context->>'phase' = '{PHASE}';
COMMIT;

SELECT 'checklist_started_remaining', count(*)::text FROM wix_staging_build_checklist_items c JOIN launch_projects p ON p.id = c.launch_project_id WHERE p.launch_key = {lk} AND c.checklist_status = 'in_progress'
UNION ALL SELECT 'checklist_passed_remaining', count(*)::text FROM wix_staging_build_checklist_items c JOIN launch_projects p ON p.id = c.launch_project_id WHERE p.launch_key = {lk} AND c.checklist_status = 'passed'
UNION ALL SELECT 'phase_7_20_action_log_rows', count(*)::text FROM wix_staging_build_action_log l JOIN launch_projects p ON p.id = l.launch_project_id WHERE p.launch_key = {lk} AND l.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'phase_7_19_checklist_items', count(*)::text FROM wix_staging_build_checklist_items c JOIN launch_projects p ON p.id = c.launch_project_id WHERE p.launch_key = {lk} AND c.raw_context->>'phase' = '7.19'
UNION ALL SELECT 'staging_sites', count(*)::text FROM wix_staging_sites s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'inbound_leads', count(*)::text FROM inbound_leads
UNION ALL SELECT 'contacts', count(*)::text FROM contacts
ORDER BY 1;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Revert Phase 7.20 Wix staging build-progress changes. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Westpark Wix staging build-progress revert. launch_key={args.launch_key}. Counts only.")
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 6:
        print("Refusing: probe returned no usable result.")
        return 1
    checklist, qa, sites, log_rows, live, inbound = (int(x or 0) for x in f[:6])
    if live or inbound:
        print("Refusing revert: live/domain/index/publish/api flags or inbound leads present.")
        print(f"  live/domain/publish/api sites: {live}   inbound_leads: {inbound}")
        return 1

    print("intended reverts (Phase 7.20 marked rows only):")
    print(f"  checklist items: {checklist}   QA checks: {qa}   staging sites: {sites}   action-log rows to delete: {log_rows}")
    print("  Phase 7.19 staging plan rows: PRESERVED (statuses restored)   contacts/leads/messages: untouched")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Reverting requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key))
    print("Revert applied:" if code == 0 else "Revert FAILED (rolled back):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
