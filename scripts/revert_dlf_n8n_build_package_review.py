#!/usr/bin/env python3
"""Phase 7.12 — revert DLF n8n build package review marks.

Dry-run by default. Reverts only rows tagged by
review_dlf_n8n_build_package.py in raw_context.phase_7_12. It does not delete
artifacts, does not touch Phase 7.11 validation rows, does not call n8n, and
does not touch leads/contacts/messages/publishing.

Writing requires BOTH --real-ok and --apply. Counts only.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PACKAGE_SOURCE = "dlf_n8n_build_package"


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
WITH pkg AS (
  SELECT bp.*
  FROM launch_n8n_build_packages bp
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk}
    AND bp.raw_context->>'source' = '{PACKAGE_SOURCE}'
),
review_marks AS (
  SELECT ri.*
  FROM launch_n8n_build_review_items ri
  JOIN pkg ON pkg.id = ri.build_package_id
  WHERE ri.raw_context ? 'phase_7_12'
),
package_marks AS (
  SELECT *
  FROM pkg
  WHERE raw_context ? 'phase_7_12'
)
SELECT
  (SELECT count(*) FROM package_marks),
  (SELECT count(*) FROM review_marks),
  (SELECT count(*) FROM pkg WHERE workflow_created_in_n8n),
  (SELECT count(*) FROM pkg WHERE activation_requested),
  (SELECT count(*) FROM launch_n8n_workflow_blueprints wb JOIN launch_projects p ON p.id = wb.launch_project_id WHERE p.launch_key = {lk} AND wb.activation_status = 'active'),
  (SELECT count(*) FROM inbound_leads),
  (SELECT count(*) FROM contacts),
  (SELECT send_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT publish_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT communication_sent FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk});
"""


def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;

DO $GUARD$
DECLARE created int; activated int; active_workflows int; inbound_count int; contacts_count int; send_count int; publish_count int; sent_count int;
BEGIN
  SELECT count(*) INTO created
  FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.workflow_created_in_n8n;
  SELECT count(*) INTO activated
  FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.activation_requested;
  SELECT count(*) INTO active_workflows
  FROM launch_n8n_workflow_blueprints wb JOIN launch_projects p ON p.id = wb.launch_project_id
  WHERE p.launch_key = {lk} AND wb.activation_status = 'active';
  SELECT count(*) INTO inbound_count FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  SELECT send_enabled_count, publish_enabled_count, communication_sent
    INTO send_count, publish_count, sent_count
  FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  IF created <> 0 OR activated <> 0 OR active_workflows <> 0 THEN RAISE EXCEPTION 'Refusing rollback: n8n creation/activation state is nonzero.'; END IF;
  IF inbound_count <> 0 THEN RAISE EXCEPTION 'Refusing rollback: inbound leads count is %.', inbound_count; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing rollback: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 OR sent_count <> 0 THEN RAISE EXCEPTION 'Refusing rollback: send/publish/communication count is nonzero.'; END IF;
END $GUARD$;

WITH pkg AS (
  SELECT bp.id
  FROM launch_n8n_build_packages bp
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk}
    AND bp.raw_context->>'source' = '{PACKAGE_SOURCE}'
),
review_revert AS (
  UPDATE launch_n8n_build_review_items ri
  SET status = COALESCE(ri.raw_context #>> '{{phase_7_12,previous_status}}', ri.status),
      reviewed_by = NULLIF(ri.raw_context #>> '{{phase_7_12,previous_reviewed_by}}', ''),
      reviewed_at = NULL,
      decision_notes = NULLIF(ri.raw_context #>> '{{phase_7_12,previous_decision_notes}}', ''),
      raw_context = ri.raw_context || jsonb_build_object(
        'phase_7_12_reverted',
        jsonb_build_object('source','revert_dlf_n8n_build_package_review')
      )
  FROM pkg
  WHERE ri.build_package_id = pkg.id
    AND ri.raw_context ? 'phase_7_12'
  RETURNING ri.id
)
UPDATE launch_n8n_build_packages bp
SET package_status = COALESCE(bp.raw_context #>> '{{phase_7_12,previous_package_status}}', bp.package_status),
    raw_context = bp.raw_context || jsonb_build_object(
      'phase_7_12_reverted',
      jsonb_build_object('source','revert_dlf_n8n_build_package_review')
    )
FROM pkg
WHERE bp.id = pkg.id
  AND bp.raw_context ? 'phase_7_12';

COMMIT;

SELECT 'package_status', package_status || '|' || count(*) FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} GROUP BY package_status
UNION ALL SELECT 'review_status', review_type || '|' || status || '|' || count(*) FROM launch_n8n_build_review_items ri JOIN launch_n8n_build_packages bp ON bp.id = ri.build_package_id JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} GROUP BY review_type, status
UNION ALL SELECT 'ready_for_manual_import', ready_for_manual_import::text FROM vw_dlf_n8n_build_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_to_activate', ready_to_activate::text FROM vw_dlf_n8n_build_readiness WHERE launch_key = {lk}
ORDER BY 1, 2;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Revert Phase 7.12 DLF n8n build package review marks. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF n8n build package review rollback. launch_key={args.launch_key}. Counts only.")
    if not args.real_ok:
        print("Refusing: --real-ok is required, even for rollback dry-run.")
        return 1
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 10:
        print("Refusing: probe returned no usable result.")
        return 1
    labels = (
        "packages_to_revert", "review_items_to_revert", "workflow_created_in_n8n",
        "activation_requested", "active_workflows", "inbound_leads", "contacts",
        "send_enabled", "publish_enabled", "communication_sent",
    )
    print("rollback candidate counts:")
    for label, value in zip(labels, fields):
        print(f"  {label}: {value}")
    if any(int(fields[i] or 0) for i in (2, 3, 4)):
        print("Refusing rollback: n8n creation/activation state is nonzero.")
        return 1
    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key))
    print("Rollback applied:" if code == 0 else "Rollback FAILED:")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
