#!/usr/bin/env python3
"""Phase 7.23 - clean up DLF Wix AI build execution plan rows.

Dry-run by default. Deletes only Phase 7.23 rows tagged raw_context.phase/source.
Artifact deletion is opt-in with --delete-artifacts. It never deletes Phase 7.19/7.20/7.22
staging records, never calls Wix APIs, and never touches leads/contacts/messages.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.23"
SOURCE = "dlf_wix_ai_build_plan"


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
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
plans AS (
  SELECT e.*
  FROM wix_ai_build_execution_plans e
  WHERE e.launch_project_id IN (SELECT id FROM proj)
    AND e.raw_context->>'phase' = '{PHASE}'
    AND e.raw_context->>'source' = '{SOURCE}'
)
SELECT
  (SELECT count(*) FROM plans),
  (SELECT count(*) FROM wix_ai_build_artifacts a JOIN plans e ON e.id = a.execution_plan_id),
  (SELECT count(*) FROM wix_ai_build_steps s JOIN plans e ON e.id = s.execution_plan_id),
  (SELECT count(*) FROM wix_ai_build_validation_results v JOIN plans e ON e.id = v.execution_plan_id),
  (SELECT count(*) FROM wix_ai_build_review_items ri JOIN plans e ON e.id = ri.execution_plan_id),
  (SELECT count(*) FROM wix_ai_build_review_items ri JOIN plans e ON e.id = ri.execution_plan_id WHERE ri.status = 'approved'),
  (SELECT count(*) FROM plans WHERE execution_status IN ('ready_for_local_code_build','ready_for_custom_element_build') ),
  (SELECT count(*) FROM plans WHERE wix_api_call_made OR external_call_made OR publish_enabled OR live_webhook_created),
  (SELECT count(*) FROM inbound_leads),
  (SELECT count(*) FROM contacts),
  (SELECT send_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT publish_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT communication_sent FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk});
"""


def artifact_paths_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT DISTINCT artifact_path
FROM wix_ai_build_artifacts a
JOIN wix_ai_build_execution_plans e ON e.id = a.execution_plan_id
JOIN launch_projects p ON p.id = e.launch_project_id
WHERE p.launch_key = {lk}
  AND a.raw_context->>'phase' = '{PHASE}'
  AND a.raw_context->>'source' = '{SOURCE}'
  AND artifact_path IS NOT NULL
ORDER BY artifact_path;
"""


def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;

DO $GUARD$
DECLARE approved int; ready_plans int; live_flags int; inbound_count int; contacts_count int; send_count int; publish_count int; sent_count int;
BEGIN
  WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
  plans AS (
    SELECT e.*
    FROM wix_ai_build_execution_plans e
    WHERE e.launch_project_id IN (SELECT id FROM proj)
      AND e.raw_context->>'phase' = '{PHASE}'
      AND e.raw_context->>'source' = '{SOURCE}'
  )
  SELECT
    (SELECT count(*) FROM wix_ai_build_review_items ri JOIN plans e ON e.id = ri.execution_plan_id WHERE ri.status = 'approved'),
    (SELECT count(*) FROM plans WHERE execution_status IN ('ready_for_local_code_build','ready_for_custom_element_build')),
    (SELECT count(*) FROM plans WHERE wix_api_call_made OR external_call_made OR publish_enabled OR live_webhook_created)
  INTO approved, ready_plans, live_flags;
  SELECT count(*) INTO inbound_count FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  SELECT send_enabled_count, publish_enabled_count, communication_sent
    INTO send_count, publish_count, sent_count
  FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  IF ready_plans > 0 AND approved > 0 THEN RAISE EXCEPTION 'Refusing cleanup: ready build plan has approved review items.'; END IF;
  IF live_flags > 0 THEN RAISE EXCEPTION 'Refusing cleanup: API/external/publish/webhook flag recorded.'; END IF;
  IF inbound_count <> 0 THEN RAISE EXCEPTION 'Refusing cleanup: inbound leads count is %.', inbound_count; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing cleanup: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 OR sent_count <> 0 THEN RAISE EXCEPTION 'Refusing cleanup: send/publish/communication count is nonzero.'; END IF;
END $GUARD$;

WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
plans AS (
  SELECT e.id
  FROM wix_ai_build_execution_plans e
  WHERE e.launch_project_id IN (SELECT id FROM proj)
    AND e.raw_context->>'phase' = '{PHASE}'
    AND e.raw_context->>'source' = '{SOURCE}'
)
DELETE FROM wix_ai_build_review_items ri USING plans e WHERE ri.execution_plan_id = e.id;

WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
plans AS (
  SELECT e.id
  FROM wix_ai_build_execution_plans e
  WHERE e.launch_project_id IN (SELECT id FROM proj)
    AND e.raw_context->>'phase' = '{PHASE}'
    AND e.raw_context->>'source' = '{SOURCE}'
)
DELETE FROM wix_ai_build_validation_results v USING plans e WHERE v.execution_plan_id = e.id;

WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
plans AS (
  SELECT e.id
  FROM wix_ai_build_execution_plans e
  WHERE e.launch_project_id IN (SELECT id FROM proj)
    AND e.raw_context->>'phase' = '{PHASE}'
    AND e.raw_context->>'source' = '{SOURCE}'
)
DELETE FROM wix_ai_build_steps s USING plans e WHERE s.execution_plan_id = e.id;

WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
plans AS (
  SELECT e.id
  FROM wix_ai_build_execution_plans e
  WHERE e.launch_project_id IN (SELECT id FROM proj)
    AND e.raw_context->>'phase' = '{PHASE}'
    AND e.raw_context->>'source' = '{SOURCE}'
)
DELETE FROM wix_ai_build_artifacts a USING plans e WHERE a.execution_plan_id = e.id;

DELETE FROM wix_ai_build_execution_plans e
USING launch_projects p
WHERE e.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND e.raw_context->>'phase' = '{PHASE}'
  AND e.raw_context->>'source' = '{SOURCE}';

COMMIT;

SELECT 'execution_plans_remaining', count(*)::text FROM wix_ai_build_execution_plans e JOIN launch_projects p ON p.id = e.launch_project_id WHERE p.launch_key = {lk} AND e.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'staging_sites_preserved', count(*)::text FROM wix_staging_sites s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'inbound_leads', count(*)::text FROM inbound_leads
UNION ALL SELECT 'contacts', count(*)::text FROM contacts
ORDER BY 1;
"""


def delete_artifacts(launch_key: str) -> int:
    code, output = run_psql(artifact_paths_sql(launch_key))
    if code != 0:
        print(output)
        return code
    deleted = 0
    root = (PROJECT_ROOT / "exports" / "wix_ai_builds").resolve()
    for rel in output.splitlines():
        if not rel.strip():
            continue
        path = (PROJECT_ROOT / rel.strip()).resolve()
        try:
            if not path.is_relative_to(root):
                print("Refusing artifact delete outside exports/wix_ai_builds.")
                return 1
            if path.exists():
                path.unlink()
                deleted += 1
        except OSError as exc:
            print(f"Artifact delete failed: {exc}")
            return 1
    print(f"artifacts_deleted: {deleted}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up Phase 7.23 DLF Wix AI build plan rows. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--delete-artifacts", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Wix AI build plan cleanup. launch_key={args.launch_key}. Counts only.")
    if not args.real_ok:
        print("Refusing: --real-ok is required, even for cleanup dry-run.")
        return 1
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 13:
        print("Refusing: probe returned no usable result.")
        return 1
    plans, artifacts, steps, validations, reviews, approved, ready_plans, live_flags, inbound, contacts, send, publish, sent = (int(x or 0) for x in fields[:13])
    if ready_plans > 0 and approved > 0:
        print("Refusing cleanup: ready build plan has approved review items.")
        return 1
    if live_flags or inbound or contacts != 4 or send or publish or sent:
        print("Refusing cleanup: live/API/lead/contact/send/publish safety count is not clean.")
        return 1

    print("intended DB deletions (Phase 7.23 rows only):")
    print(f"  execution plans: {plans}   artifacts: {artifacts}   steps: {steps}   validations: {validations}   reviews: {reviews}")
    print(f"  artifact_delete_requested: {str(args.delete_artifacts).lower()}")
    print("  Phase 7.19/7.20/7.22 staging-site records: UNTOUCHED")
    if not (args.apply and args.real_ok):
        print("Dry run only. No database or artifact writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    if args.delete_artifacts:
        code = delete_artifacts(args.launch_key)
        if code != 0:
            return code

    code, output = run_psql(apply_sql(args.launch_key))
    print("Cleanup applied:" if code == 0 else "Cleanup FAILED:")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
