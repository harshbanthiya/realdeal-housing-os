#!/usr/bin/env python3
"""Phase 7.13 — record a human-only DLF n8n manual import check.

Dry-run by default. This never calls n8n, never imports/creates/activates a
workflow, never creates a live webhook, never creates leads/contacts, and never
enables sends or publishing.

If no workflow id/name is supplied, it records a pending no-import check. If a
workflow id/name and all inactive/no-secret/no-live confirmations are supplied,
it records an imported-inactive verification and updates package/blueprint state
only to inactive-created metadata. Writing requires BOTH --real-ok and --apply.
Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.13"
SOURCE = "dlf_n8n_manual_import_check"
PACKAGE_SOURCE = "dlf_n8n_build_package"
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT
  (SELECT count(*) FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.package_status = 'approved_for_manual_import'),
  (SELECT count(*) FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.workflow_created_in_n8n),
  (SELECT count(*) FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.activation_requested),
  (SELECT count(*) FROM launch_n8n_workflow_blueprints wb JOIN launch_projects p ON p.id = wb.launch_project_id WHERE p.launch_key = {lk} AND wb.activation_status = 'active'),
  (SELECT count(*) FROM launch_n8n_manual_import_checks mic JOIN launch_projects p ON p.id = mic.launch_project_id WHERE p.launch_key = {lk}),
  (SELECT count(*) FROM inbound_leads),
  (SELECT count(*) FROM contacts),
  (SELECT send_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT publish_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT communication_sent FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT ready_for_live_lead_capture::text FROM vw_dlf_test_lead_readiness WHERE launch_key = {lk}),
  (SELECT ready_for_launch_push::text FROM vw_dlf_launch_activation_guardrail WHERE launch_key = {lk}),
  (SELECT ready_to_activate::text FROM vw_dlf_n8n_build_readiness WHERE launch_key = {lk});
"""

def apply_sql(args: argparse.Namespace, imported: bool) -> str:
    lk = sql_literal(args.launch_key)
    checked_by = sql_literal(args.checked_by)
    notes = sql_literal(args.decision_notes)
    workflow_id = sql_literal(args.operator_reported_workflow_id)
    workflow_name = sql_literal(args.operator_reported_workflow_name)
    status = "imported_inactive_verified" if imported else "pending"
    summary = (
        "Operator reported inactive manual import; activation remains blocked."
        if imported else
        "Manual import not yet performed; package remains approved for manual import only."
    )
    return f"""
BEGIN;

DO $GUARD$
DECLARE
  approved_packages int; created int; activated int; active_workflows int;
  inbound_count int; contacts_count int; send_count int; publish_count int; sent_count int;
  live_capture boolean; launch_push boolean; ready_activate boolean;
BEGIN
  SELECT count(*) INTO approved_packages
  FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.package_status = 'approved_for_manual_import';
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
  SELECT ready_for_live_lead_capture INTO live_capture FROM vw_dlf_test_lead_readiness WHERE launch_key = {lk};
  SELECT ready_for_launch_push INTO launch_push FROM vw_dlf_launch_activation_guardrail WHERE launch_key = {lk};
  SELECT ready_to_activate INTO ready_activate FROM vw_dlf_n8n_build_readiness WHERE launch_key = {lk};
  IF approved_packages <> 1 THEN RAISE EXCEPTION 'Refusing: expected 1 package approved_for_manual_import, found %.', approved_packages; END IF;
  IF activated <> 0 OR active_workflows <> 0 THEN RAISE EXCEPTION 'Refusing: activation state is nonzero.'; END IF;
  IF inbound_count <> 0 THEN RAISE EXCEPTION 'Refusing: inbound leads count is %.', inbound_count; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 OR sent_count <> 0 THEN RAISE EXCEPTION 'Refusing: send/publish/communication count is nonzero.'; END IF;
  IF live_capture OR launch_push OR ready_activate THEN RAISE EXCEPTION 'Refusing: live/launch/activation readiness is true.'; END IF;
END $GUARD$;

WITH project AS (
  SELECT id FROM launch_projects WHERE launch_key = {lk}
),
pkg AS (
  SELECT bp.*
  FROM launch_n8n_build_packages bp
  JOIN project p ON p.id = bp.launch_project_id
  WHERE bp.package_status = 'approved_for_manual_import'
  ORDER BY bp.created_at
  LIMIT 1
),
blueprint AS (
  SELECT wb.*
  FROM launch_n8n_workflow_blueprints wb
  JOIN pkg bp ON bp.workflow_blueprint_id = wb.id
  LIMIT 1
),
inserted AS (
INSERT INTO launch_n8n_manual_import_checks
  (launch_project_id, build_package_id, workflow_blueprint_id, check_status,
   operator_reported_n8n_workflow_id, operator_reported_workflow_name,
   verified_inactive, verified_no_credentials, verified_no_live_webhook, verified_not_active,
   activation_requested, external_call_made, checked_by, checked_at, safe_summary, raw_context)
SELECT
  p.id, bp.id, b.id, {sql_literal(status)},
  {workflow_id}, {workflow_name},
  {str(imported).lower()}::boolean, {str(args.confirm_no_credentials).lower()}::boolean,
  {str(args.confirm_no_live_webhook).lower()}::boolean, {str(args.confirm_not_active).lower()}::boolean,
  false, false, {checked_by}, now(), {sql_literal(summary)},
  jsonb_build_object('phase','{PHASE}','source','{SOURCE}','no_import_path',{str(not imported).lower()}::boolean)
FROM project p
JOIN pkg bp ON true
JOIN blueprint b ON true
RETURNING id
)
SELECT count(*) AS inserted_manual_import_checks FROM inserted;

UPDATE launch_n8n_build_packages bp
SET package_status = 'imported_inactive',
    workflow_created_in_n8n = true,
    activation_requested = false,
    raw_context = bp.raw_context || jsonb_build_object(
      'phase_7_13',
      jsonb_build_object(
        'phase','{PHASE}',
        'source','{SOURCE}',
        'previous_package_status', bp.package_status,
        'previous_workflow_created_in_n8n', bp.workflow_created_in_n8n,
        'operator_reported_n8n_workflow_id', {workflow_id},
        'operator_reported_workflow_name', {workflow_name}
      )
    )
FROM launch_projects p
WHERE bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND {str(imported).lower()}::boolean;

UPDATE launch_n8n_workflow_blueprints wb
SET workflow_status = 'built_in_n8n',
    activation_status = 'created_inactive',
    n8n_workflow_id = {workflow_id},
    raw_context = wb.raw_context || jsonb_build_object(
      'phase_7_13',
      jsonb_build_object(
        'phase','{PHASE}',
        'source','{SOURCE}',
        'previous_workflow_status', wb.workflow_status,
        'previous_activation_status', wb.activation_status,
        'previous_n8n_workflow_id', wb.n8n_workflow_id,
        'operator_reported_workflow_name', {workflow_name}
      )
    )
FROM launch_n8n_build_packages bp
WHERE bp.workflow_blueprint_id = wb.id
  AND {str(imported).lower()}::boolean
  AND wb.activation_status <> 'active';

DO $POST_GUARD$
DECLARE activated int; active_workflows int; ready_activate boolean; live_capture boolean; launch_push boolean;
BEGIN
  SELECT count(*) INTO activated FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.activation_requested;
  SELECT count(*) INTO active_workflows FROM launch_n8n_workflow_blueprints wb JOIN launch_projects p ON p.id = wb.launch_project_id WHERE p.launch_key = {lk} AND wb.activation_status = 'active';
  SELECT ready_to_activate INTO ready_activate FROM vw_dlf_n8n_build_readiness WHERE launch_key = {lk};
  SELECT ready_for_live_lead_capture INTO live_capture FROM vw_dlf_test_lead_readiness WHERE launch_key = {lk};
  SELECT ready_for_launch_push INTO launch_push FROM vw_dlf_launch_activation_guardrail WHERE launch_key = {lk};
  IF activated <> 0 OR active_workflows <> 0 THEN RAISE EXCEPTION 'Refusing: activation state changed.'; END IF;
  IF ready_activate OR live_capture OR launch_push THEN RAISE EXCEPTION 'Refusing: activation/live/launch readiness became true.'; END IF;
END $POST_GUARD$;

COMMIT;

SELECT 'manual_import_checks', check_status || '|' || count(*) FROM launch_n8n_manual_import_checks mic JOIN launch_projects p ON p.id = mic.launch_project_id WHERE p.launch_key = {lk} GROUP BY check_status
UNION ALL SELECT 'packages', package_status || '|' || workflow_created_in_n8n::text || '|' || activation_requested::text || '|' || count(*) FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} GROUP BY package_status, workflow_created_in_n8n, activation_requested
UNION ALL SELECT 'blueprints', workflow_status || '|' || activation_status || '|' || count(*) FROM launch_n8n_workflow_blueprints wb JOIN launch_projects p ON p.id = wb.launch_project_id WHERE p.launch_key = {lk} GROUP BY workflow_status, activation_status
UNION ALL SELECT 'ready_for_inactive_manual_import', ready_for_inactive_manual_import::text FROM vw_dlf_n8n_manual_import_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_to_activate', ready_to_activate::text FROM vw_dlf_n8n_manual_import_readiness WHERE launch_key = {lk}
ORDER BY 1, 2;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Record DLF n8n manual import verification. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--checked-by", default="")
    parser.add_argument("--decision-notes", default="")
    parser.add_argument("--operator-reported-workflow-id")
    parser.add_argument("--operator-reported-workflow-name")
    parser.add_argument("--confirm-imported-inactive", action="store_true")
    parser.add_argument("--confirm-no-credentials", action="store_true")
    parser.add_argument("--confirm-no-live-webhook", action="store_true")
    parser.add_argument("--confirm-not-active", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF n8n manual import check. launch_key={args.launch_key}. Counts only.")
    if not args.real_ok:
        print("Refusing: --real-ok is required, even for dry-run.")
        return 1
    if args.apply and (not args.checked_by or not args.decision_notes):
        print("Refusing: --checked-by and --decision-notes are required for apply.")
        return 1

    supplied_workflow = bool(args.operator_reported_workflow_id or args.operator_reported_workflow_name)
    imported = bool(
        supplied_workflow
        and args.confirm_imported_inactive
        and args.confirm_no_credentials
        and args.confirm_no_live_webhook
        and args.confirm_not_active
    )
    if supplied_workflow and not imported:
        print("Refusing: workflow details require all inactive/no-credential/no-live/not-active confirmations.")
        return 1

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    labels = (
        "approved_packages", "workflow_created_in_n8n", "activation_requested", "active_workflows",
        "existing_manual_import_checks", "inbound_leads", "contacts", "send_enabled",
        "publish_enabled", "communication_sent", "ready_for_live_lead_capture",
        "ready_for_launch_push", "ready_to_activate",
    )
    print("baseline:")
    for label, value in zip(labels, fields):
        print(f"  {label}: {value}")
    print("projected:")
    print(f"  manual_import_check_status: {'imported_inactive_verified' if imported else 'pending'}")
    print(f"  workflow_created_in_n8n_after: {str(imported).lower()}")
    print("  activation_requested_after: false")
    print("  ready_to_activate_after: false")
    print("  n8n_api_calls: 0   live_webhooks: 0   leads_or_contacts: 0")

    if not args.apply:
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args, imported))
    print("Apply result:" if code == 0 else "Apply FAILED:")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
