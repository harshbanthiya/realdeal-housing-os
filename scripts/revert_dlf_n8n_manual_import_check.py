#!/usr/bin/env python3
"""Phase 7.13 — revert DLF n8n manual import verification rows.

Dry-run by default. Reverts only rows tagged by
record_dlf_n8n_manual_import_check.py in raw_context.phase/source. It does not
delete artifacts, does not call n8n, does not touch leads/contacts/messages, and
never activates a workflow. Writing requires BOTH --real-ok and --apply.
Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.13"
SOURCE = "dlf_n8n_manual_import_check"
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH phase_checks AS (
  SELECT mic.*
  FROM launch_n8n_manual_import_checks mic
  JOIN launch_projects p ON p.id = mic.launch_project_id
  WHERE p.launch_key = {lk}
    AND mic.raw_context->>'phase' = '{PHASE}'
    AND mic.raw_context->>'source' = '{SOURCE}'
),
phase_packages AS (
  SELECT bp.*
  FROM launch_n8n_build_packages bp
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk}
    AND bp.raw_context ? 'phase_7_13'
),
phase_blueprints AS (
  SELECT wb.*
  FROM launch_n8n_workflow_blueprints wb
  JOIN launch_projects p ON p.id = wb.launch_project_id
  WHERE p.launch_key = {lk}
    AND wb.raw_context ? 'phase_7_13'
)
SELECT
  (SELECT count(*) FROM phase_checks),
  (SELECT count(*) FROM phase_checks WHERE check_status = 'pending'),
  (SELECT count(*) FROM phase_checks WHERE check_status = 'imported_inactive_verified'),
  (SELECT count(*) FROM phase_packages),
  (SELECT count(*) FROM phase_blueprints),
  (SELECT count(*) FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.activation_requested),
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
DECLARE activated int; active_workflows int; inbound_count int; contacts_count int; send_count int; publish_count int; sent_count int;
BEGIN
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
  IF activated <> 0 OR active_workflows <> 0 THEN RAISE EXCEPTION 'Refusing rollback: activation state is nonzero.'; END IF;
  IF inbound_count <> 0 THEN RAISE EXCEPTION 'Refusing rollback: inbound leads count is %.', inbound_count; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing rollback: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 OR sent_count <> 0 THEN RAISE EXCEPTION 'Refusing rollback: send/publish/communication count is nonzero.'; END IF;
END $GUARD$;

UPDATE launch_n8n_build_packages bp
SET package_status = COALESCE(bp.raw_context #>> '{{phase_7_13,previous_package_status}}', bp.package_status),
    workflow_created_in_n8n = COALESCE((bp.raw_context #>> '{{phase_7_13,previous_workflow_created_in_n8n}}')::boolean, bp.workflow_created_in_n8n),
    activation_requested = false,
    raw_context = bp.raw_context || jsonb_build_object(
      'phase_7_13_reverted',
      jsonb_build_object('source','revert_dlf_n8n_manual_import_check')
    )
FROM launch_projects p
WHERE bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context ? 'phase_7_13';

UPDATE launch_n8n_workflow_blueprints wb
SET workflow_status = COALESCE(wb.raw_context #>> '{{phase_7_13,previous_workflow_status}}', wb.workflow_status),
    activation_status = COALESCE(wb.raw_context #>> '{{phase_7_13,previous_activation_status}}', wb.activation_status),
    n8n_workflow_id = NULLIF(wb.raw_context #>> '{{phase_7_13,previous_n8n_workflow_id}}', ''),
    raw_context = wb.raw_context || jsonb_build_object(
      'phase_7_13_reverted',
      jsonb_build_object('source','revert_dlf_n8n_manual_import_check')
    )
FROM launch_projects p
WHERE wb.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND wb.raw_context ? 'phase_7_13';

DELETE FROM launch_n8n_manual_import_checks mic
USING launch_projects p
WHERE mic.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND mic.raw_context->>'phase' = '{PHASE}'
  AND mic.raw_context->>'source' = '{SOURCE}';

COMMIT;

SELECT 'manual_import_checks_remaining', count(*)::text FROM launch_n8n_manual_import_checks mic JOIN launch_projects p ON p.id = mic.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'packages', package_status || '|' || workflow_created_in_n8n::text || '|' || activation_requested::text || '|' || count(*) FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} GROUP BY package_status, workflow_created_in_n8n, activation_requested
UNION ALL SELECT 'blueprints', workflow_status || '|' || activation_status || '|' || count(*) FROM launch_n8n_workflow_blueprints wb JOIN launch_projects p ON p.id = wb.launch_project_id WHERE p.launch_key = {lk} GROUP BY workflow_status, activation_status
UNION ALL SELECT 'ready_to_activate', ready_to_activate::text FROM vw_dlf_n8n_manual_import_readiness WHERE launch_key = {lk}
ORDER BY 1, 2;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Revert Phase 7.13 DLF n8n manual import checks. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF n8n manual import check rollback. launch_key={args.launch_key}. Counts only.")
    if not args.real_ok:
        print("Refusing: --real-ok is required, even for rollback dry-run.")
        return 1

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 12:
        print("Refusing: probe returned no usable result.")
        return 1
    labels = (
        "phase_7_13_checks_to_delete", "pending_checks", "imported_inactive_checks",
        "packages_to_restore", "blueprints_to_restore", "activation_requested",
        "active_workflows", "inbound_leads", "contacts", "send_enabled",
        "publish_enabled", "communication_sent",
    )
    print("rollback candidate counts:")
    for label, value in zip(labels, fields):
        print(f"  {label}: {value}")
    if any(int(fields[i] or 0) for i in (5, 6)):
        print("Refusing rollback: activation_requested or active workflow count is nonzero.")
        return 1
    if fields[7] != "0" or fields[8] != "4" or any(int(fields[i] or 0) for i in (9, 10, 11)):
        print("Refusing rollback: lead/contact/send/publish safety count changed.")
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
