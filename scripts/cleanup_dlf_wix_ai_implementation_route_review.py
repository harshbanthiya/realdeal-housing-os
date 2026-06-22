#!/usr/bin/env python3
"""Phase 7.24 - clean up DLF Wix AI implementation route-review rows.

Dry-run by default. Deletes only Phase 7.24 rows tagged raw_context.phase/source. It does not
delete Phase 7.23 execution plans/artifacts or ignored exports files, and it never calls Wix APIs
or touches leads/contacts/messages.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.24"
SOURCE = "dlf_wix_ai_implementation_route_review"
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
decisions AS (
  SELECT rd.*
  FROM wix_ai_implementation_route_decisions rd
  WHERE rd.launch_project_id IN (SELECT id FROM proj)
    AND rd.raw_context->>'phase' = '{PHASE}'
    AND rd.raw_context->>'source' = '{SOURCE}'
)
SELECT
  (SELECT count(*) FROM decisions),
  (SELECT count(*) FROM wix_ai_artifact_review_results ar JOIN decisions rd ON rd.id = ar.route_decision_id),
  (SELECT count(*) FROM wix_ai_operator_setup_tasks t JOIN decisions rd ON rd.id = t.route_decision_id),
  (SELECT count(*) FROM wix_ai_execution_package_steps s JOIN decisions rd ON rd.id = s.route_decision_id),
  (SELECT count(*) FROM wix_ai_implementation_review_items ri JOIN decisions rd ON rd.id = ri.route_decision_id),
  (SELECT count(*) FROM decisions WHERE route_decision_status = 'approved_for_operator_setup'),
  (SELECT count(*) FROM wix_ai_implementation_review_items ri JOIN decisions rd ON rd.id = ri.route_decision_id WHERE ri.status = 'approved'),
  (SELECT count(*) FROM decisions WHERE requires_wix_api_key OR requires_publish_permission OR requires_live_webhook),
  (SELECT count(*) FROM wix_ai_build_execution_plans e JOIN launch_projects p ON p.id = e.launch_project_id WHERE p.launch_key = {lk}),
  (SELECT count(*) FROM wix_ai_build_artifacts a JOIN launch_projects p ON p.id = a.launch_project_id WHERE p.launch_key = {lk}),
  (SELECT count(*) FROM inbound_leads),
  (SELECT count(*) FROM contacts),
  (SELECT send_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT publish_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT communication_sent FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk});
"""

def delete_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;

DO $GUARD$
DECLARE approved_decisions int; approved_reviews int; unsafe_flags int;
BEGIN
  WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
  decisions AS (
    SELECT rd.*
    FROM wix_ai_implementation_route_decisions rd
    WHERE rd.launch_project_id IN (SELECT id FROM proj)
      AND rd.raw_context->>'phase' = '{PHASE}'
      AND rd.raw_context->>'source' = '{SOURCE}'
  )
  SELECT
    (SELECT count(*) FROM decisions WHERE route_decision_status = 'approved_for_operator_setup'),
    (SELECT count(*) FROM wix_ai_implementation_review_items ri JOIN decisions rd ON rd.id = ri.route_decision_id WHERE ri.status = 'approved'),
    (SELECT count(*) FROM decisions WHERE requires_wix_api_key OR requires_publish_permission OR requires_live_webhook)
  INTO approved_decisions, approved_reviews, unsafe_flags;
  IF approved_decisions > 0 THEN RAISE EXCEPTION 'Refusing cleanup: approved_for_operator_setup decision exists.'; END IF;
  IF approved_reviews > 0 THEN RAISE EXCEPTION 'Refusing cleanup: approved implementation review exists.'; END IF;
  IF unsafe_flags > 0 THEN RAISE EXCEPTION 'Refusing cleanup: unsafe route flag exists.'; END IF;
END $GUARD$;

WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
decisions AS (
  SELECT rd.id
  FROM wix_ai_implementation_route_decisions rd
  WHERE rd.launch_project_id IN (SELECT id FROM proj)
    AND rd.raw_context->>'phase' = '{PHASE}'
    AND rd.raw_context->>'source' = '{SOURCE}'
)
DELETE FROM wix_ai_implementation_review_items ri USING decisions rd WHERE ri.route_decision_id = rd.id;

WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
decisions AS (
  SELECT rd.id
  FROM wix_ai_implementation_route_decisions rd
  WHERE rd.launch_project_id IN (SELECT id FROM proj)
    AND rd.raw_context->>'phase' = '{PHASE}'
    AND rd.raw_context->>'source' = '{SOURCE}'
)
DELETE FROM wix_ai_execution_package_steps s USING decisions rd WHERE s.route_decision_id = rd.id;

WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
decisions AS (
  SELECT rd.id
  FROM wix_ai_implementation_route_decisions rd
  WHERE rd.launch_project_id IN (SELECT id FROM proj)
    AND rd.raw_context->>'phase' = '{PHASE}'
    AND rd.raw_context->>'source' = '{SOURCE}'
)
DELETE FROM wix_ai_operator_setup_tasks t USING decisions rd WHERE t.route_decision_id = rd.id;

WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
decisions AS (
  SELECT rd.id
  FROM wix_ai_implementation_route_decisions rd
  WHERE rd.launch_project_id IN (SELECT id FROM proj)
    AND rd.raw_context->>'phase' = '{PHASE}'
    AND rd.raw_context->>'source' = '{SOURCE}'
)
DELETE FROM wix_ai_artifact_review_results ar USING decisions rd WHERE ar.route_decision_id = rd.id;

DELETE FROM wix_ai_implementation_route_decisions rd
USING launch_projects p
WHERE rd.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND rd.raw_context->>'phase' = '{PHASE}'
  AND rd.raw_context->>'source' = '{SOURCE}';

COMMIT;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up Phase 7.24 Wix AI implementation route review rows. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Wix AI implementation route review cleanup. launch_key={args.launch_key}. Counts only.")
    if not args.real_ok:
        print("Refusing: --real-ok is required, even for cleanup dry-run.")
        return 1
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = [int(x or 0) for x in probe.split("|")[:15]]
    if len(fields) < 15:
        print("Refusing: probe returned no usable result.")
        return 1
    decisions, artifacts, tasks, steps, reviews, approved_decisions, approved_reviews, unsafe_flags, build_plans, build_artifacts, inbound, contacts, send, publish, sent = fields
    if approved_decisions or approved_reviews or unsafe_flags:
        print("Refusing cleanup: approved review/decision or unsafe route flag exists.")
        return 1
    if inbound or contacts != 4 or send or publish or sent:
        print("Refusing cleanup: lead/contact/send/publish/communication count is not clean.")
        return 1

    print("intended DB deletions (Phase 7.24 rows only):")
    print(f"  route decisions: {decisions}   artifact reviews: {artifacts}   operator tasks: {tasks}")
    print(f"  AI execution steps: {steps}   implementation reviews: {reviews}")
    print(f"  Phase 7.23 execution plans/artifacts preserved: {build_plans}/{build_artifacts}")
    print("  ignored exports artifacts: UNTOUCHED")
    if not args.apply:
        print("Dry run only. No database or artifact writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(delete_sql(args.launch_key))
    if code != 0:
        print(output)
        return code
    print("Cleanup applied. Phase 7.23 rows and exports artifacts were not deleted.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
