#!/usr/bin/env python3
"""Phase 7.12 — review the DLF inactive n8n build package.

Dry-run by default. This script only updates Phase 7.11 build-package review
rows and the package status for manual import readiness. It never calls n8n,
never imports/creates/activates a workflow, never creates a webhook, never
touches leads/contacts, and never enables send/publish.

Writing requires BOTH --real-ok and --apply. Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.12"
SOURCE = "dlf_n8n_build_package_review"
PACKAGE_SOURCE = "dlf_n8n_build_package"
REQUIRED_REVIEWS = (
    "build_package_review",
    "security_review",
    "privacy_review",
    "manual_import_review",
)
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
required_reviews AS (
  SELECT ri.*
  FROM launch_n8n_build_review_items ri
  JOIN pkg ON pkg.id = ri.build_package_id
  WHERE ri.review_type IN ('build_package_review','security_review','privacy_review','manual_import_review')
),
activation_reviews AS (
  SELECT ri.*
  FROM launch_n8n_build_review_items ri
  JOIN pkg ON pkg.id = ri.build_package_id
  WHERE ri.review_type = 'activation_blocker_review'
)
SELECT
  (SELECT count(*) FROM pkg),
  (SELECT count(*) FROM pkg WHERE package_status = 'validated'),
  (SELECT count(*) FROM pkg WHERE package_status = 'approved_for_manual_import'),
  (SELECT count(*) FROM launch_n8n_build_validation_results vr JOIN pkg ON pkg.id = vr.build_package_id),
  (SELECT count(*) FROM launch_n8n_build_validation_results vr JOIN pkg ON pkg.id = vr.build_package_id WHERE vr.validation_status = 'passed'),
  (SELECT count(*) FROM launch_n8n_build_validation_results vr JOIN pkg ON pkg.id = vr.build_package_id WHERE vr.validation_status = 'failed'),
  (SELECT count(*) FROM required_reviews),
  (SELECT count(*) FROM required_reviews WHERE status = 'approved'),
  (SELECT count(*) FROM activation_reviews),
  (SELECT count(*) FROM activation_reviews WHERE status IN ('pending','needs_more_info')),
  (SELECT count(*) FROM pkg WHERE workflow_created_in_n8n),
  (SELECT count(*) FROM pkg WHERE activation_requested),
  (SELECT count(*) FROM launch_n8n_workflow_blueprints wb JOIN launch_projects p ON p.id = wb.launch_project_id WHERE p.launch_key = {lk} AND wb.activation_status = 'active'),
  (SELECT count(*) FROM inbound_leads),
  (SELECT count(*) FROM contacts),
  (SELECT send_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT publish_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT communication_sent FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT ready_for_live_lead_capture::text FROM vw_dlf_test_lead_readiness WHERE launch_key = {lk}),
  (SELECT ready_for_launch_push::text FROM vw_dlf_launch_activation_guardrail WHERE launch_key = {lk}),
  (SELECT ready_to_activate::text FROM vw_dlf_n8n_build_readiness WHERE launch_key = {lk});
"""

def apply_sql(args: argparse.Namespace) -> str:
    lk = sql_literal(args.launch_key)
    reviewer = sql_literal(args.reviewed_by)
    notes = sql_literal(args.decision_notes)
    approved_reviews = []
    if args.approve_safe_build_package:
        approved_reviews.append("build_package_review")
    if args.approve_security_review:
        approved_reviews.append("security_review")
    if args.approve_privacy_review:
        approved_reviews.append("privacy_review")
    if args.approve_manual_import_review:
        approved_reviews.append("manual_import_review")
    approved_values = ", ".join(sql_literal(r) for r in approved_reviews) or "NULL"
    return f"""
BEGIN;

DO $GUARD$
DECLARE
  packages int; validation_failures int; created int; activated int; active_workflows int;
  inbound_count int; contacts_count int; send_count int; publish_count int; sent_count int;
  live_capture boolean; launch_push boolean; ready_activate boolean;
BEGIN
  SELECT count(*) INTO packages
  FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.raw_context->>'source' = '{PACKAGE_SOURCE}';
  SELECT count(*) INTO validation_failures
  FROM launch_n8n_build_validation_results vr
  JOIN launch_n8n_build_packages bp ON bp.id = vr.build_package_id
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.raw_context->>'source' = '{PACKAGE_SOURCE}'
    AND vr.validation_status <> 'passed';
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

  IF packages <> 1 THEN RAISE EXCEPTION 'Refusing: expected exactly 1 Phase 7.11 build package, found %.', packages; END IF;
  IF validation_failures <> 0 THEN RAISE EXCEPTION 'Refusing: validation failure/non-passed count is %.', validation_failures; END IF;
  IF created <> 0 OR activated <> 0 OR active_workflows <> 0 THEN RAISE EXCEPTION 'Refusing: n8n creation/activation state is nonzero.'; END IF;
  IF inbound_count <> 0 THEN RAISE EXCEPTION 'Refusing: inbound leads count is %.', inbound_count; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 OR sent_count <> 0 THEN RAISE EXCEPTION 'Refusing: send/publish/communication count is nonzero.'; END IF;
  IF live_capture OR launch_push OR ready_activate THEN RAISE EXCEPTION 'Refusing: live/launch/activation readiness became true.'; END IF;
END $GUARD$;

WITH pkg AS (
  SELECT bp.id
  FROM launch_n8n_build_packages bp
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk}
    AND bp.raw_context->>'source' = '{PACKAGE_SOURCE}'
),
updated_reviews AS (
  UPDATE launch_n8n_build_review_items ri
  SET status = 'approved',
      reviewed_by = {reviewer},
      reviewed_at = now(),
      decision_notes = {notes},
      raw_context = ri.raw_context || jsonb_build_object(
        'phase_7_12',
        jsonb_build_object(
          'phase','{PHASE}',
          'source','{SOURCE}',
          'previous_status', ri.status,
          'previous_reviewed_by', ri.reviewed_by,
          'previous_decision_notes', ri.decision_notes
        )
      )
  FROM pkg
  WHERE ri.build_package_id = pkg.id
    AND ri.review_type IN ({approved_values})
  RETURNING ri.id
),
blocked_activation AS (
  UPDATE launch_n8n_build_review_items ri
  SET status = 'needs_more_info',
      reviewed_by = {reviewer},
      reviewed_at = now(),
      decision_notes = {sql_literal('Manual import may be reviewed, but activation remains blocked for a later explicit phase.')},
      raw_context = ri.raw_context || jsonb_build_object(
        'phase_7_12',
        jsonb_build_object(
          'phase','{PHASE}',
          'source','{SOURCE}',
          'previous_status', ri.status,
          'previous_reviewed_by', ri.reviewed_by,
          'previous_decision_notes', ri.decision_notes
        )
      )
  FROM pkg
  WHERE ri.build_package_id = pkg.id
    AND ri.review_type = 'activation_blocker_review'
    AND {str(args.leave_activation_blocked).lower()}::boolean
  RETURNING ri.id
)
SELECT 1;

WITH pkg AS (
  SELECT bp.id
  FROM launch_n8n_build_packages bp
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk}
    AND bp.raw_context->>'source' = '{PACKAGE_SOURCE}'
),
approved_required AS (
  SELECT count(*) AS approved_count
  FROM launch_n8n_build_review_items ri
  JOIN pkg ON pkg.id = ri.build_package_id
  WHERE ri.review_type IN ('build_package_review','security_review','privacy_review','manual_import_review')
    AND ri.status = 'approved'
),
validation_state AS (
  SELECT count(*) FILTER (WHERE vr.validation_status <> 'passed') AS non_passed
  FROM launch_n8n_build_validation_results vr
  JOIN pkg ON pkg.id = vr.build_package_id
)
UPDATE launch_n8n_build_packages bp
SET package_status = 'approved_for_manual_import',
    raw_context = bp.raw_context || jsonb_build_object(
      'phase_7_12',
      jsonb_build_object(
        'phase','{PHASE}',
        'source','{SOURCE}',
        'previous_package_status', bp.package_status,
        'approved_for_manual_import_by', {reviewer}
      )
    )
FROM pkg, approved_required ar, validation_state vs
WHERE bp.id = pkg.id
  AND ar.approved_count = 4
  AND vs.non_passed = 0;

DO $POST_GUARD$
DECLARE created int; activated int; active_workflows int; ready_activate boolean; live_capture boolean; launch_push boolean;
BEGIN
  SELECT count(*) INTO created FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.workflow_created_in_n8n;
  SELECT count(*) INTO activated FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.activation_requested;
  SELECT count(*) INTO active_workflows FROM launch_n8n_workflow_blueprints wb JOIN launch_projects p ON p.id = wb.launch_project_id WHERE p.launch_key = {lk} AND wb.activation_status = 'active';
  SELECT ready_to_activate INTO ready_activate FROM vw_dlf_n8n_build_readiness WHERE launch_key = {lk};
  SELECT ready_for_live_lead_capture INTO live_capture FROM vw_dlf_test_lead_readiness WHERE launch_key = {lk};
  SELECT ready_for_launch_push INTO launch_push FROM vw_dlf_launch_activation_guardrail WHERE launch_key = {lk};
  IF created <> 0 OR activated <> 0 OR active_workflows <> 0 THEN RAISE EXCEPTION 'Refusing: n8n creation/activation changed.'; END IF;
  IF ready_activate OR live_capture OR launch_push THEN RAISE EXCEPTION 'Refusing: activation/live/launch readiness became true.'; END IF;
END $POST_GUARD$;

COMMIT;

SELECT 'package_status', package_status || '|' || count(*) FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} GROUP BY package_status
UNION ALL SELECT 'review_status', review_type || '|' || status || '|' || count(*) FROM launch_n8n_build_review_items ri JOIN launch_n8n_build_packages bp ON bp.id = ri.build_package_id JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} GROUP BY review_type, status
UNION ALL SELECT 'ready_for_manual_import', ready_for_manual_import::text FROM vw_dlf_n8n_build_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_to_activate', ready_to_activate::text FROM vw_dlf_n8n_build_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'workflow_created_in_n8n', count(*)::text FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.workflow_created_in_n8n
UNION ALL SELECT 'activation_requested', count(*)::text FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.activation_requested
ORDER BY 1, 2;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Review DLF inactive n8n build package. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--reviewed-by", default="")
    parser.add_argument("--decision-notes", default="")
    parser.add_argument("--approve-safe-build-package", action="store_true")
    parser.add_argument("--approve-security-review", action="store_true")
    parser.add_argument("--approve-privacy-review", action="store_true")
    parser.add_argument("--approve-manual-import-review", action="store_true")
    parser.add_argument("--leave-activation-blocked", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF n8n build package review. launch_key={args.launch_key}. Counts only.")
    if not args.real_ok:
        print("Refusing: --real-ok is required, even for dry-run review.")
        return 1
    if args.apply and (not args.reviewed_by or not args.decision_notes):
        print("Refusing: --reviewed-by and --decision-notes are required for apply.")
        return 1
    if not args.leave_activation_blocked:
        print("Refusing: --leave-activation-blocked is required. Activation approval is out of scope.")
        return 1

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 21:
        print("Refusing: baseline probe returned no usable result.")
        return 1
    labels = (
        "packages", "packages_validated", "packages_approved_for_manual_import", "validations_total",
        "validations_passed", "validation_failures", "required_reviews", "required_reviews_approved",
        "activation_reviews", "activation_reviews_blocked_or_pending", "workflow_created_in_n8n",
        "activation_requested", "active_workflows", "inbound_leads", "contacts", "send_enabled",
        "publish_enabled", "communication_sent", "ready_for_live_lead_capture",
        "ready_for_launch_push", "ready_to_activate",
    )
    print("baseline:")
    for label, value in zip(labels, fields):
        print(f"  {label}: {value}")
    print("projected:")
    print("  safe reviews approved: 4")
    print("  activation review: needs_more_info")
    print("  package_status: approved_for_manual_import")
    print("  n8n_api_calls: 0   workflow_imports: 0   activation_requested: 0")
    print("  inbound_leads_created: 0   contacts_created_or_merged: 0   sends_or_publishing: 0")

    if not args.apply:
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args))
    print("Apply result:" if code == 0 else "Apply FAILED:")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
