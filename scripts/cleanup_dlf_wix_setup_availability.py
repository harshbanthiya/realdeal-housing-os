#!/usr/bin/env python3
"""Phase 7.25 - clean up DLF Wix setup availability rows.

Dry-run by default. Deletes only Phase 7.25 rows tagged raw_context.phase/source. It does not
delete Phase 7.24 route decisions/artifact reviews or ignored exports artifacts.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.25"
SOURCE = "dlf_wix_setup_availability"


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
    return result.returncode, result.stdout.strip() or result.stderr.strip()


def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
paths AS (
  SELECT sp.*
  FROM wix_ai_selected_execution_paths sp
  WHERE sp.launch_project_id IN (SELECT id FROM proj)
    AND sp.raw_context->>'phase' = '{PHASE}'
    AND sp.raw_context->>'source' = '{SOURCE}'
)
SELECT
  (SELECT count(*) FROM wix_ai_setup_availability_checks c WHERE c.launch_project_id IN (SELECT id FROM proj) AND c.raw_context->>'phase' = '{PHASE}' AND c.raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM paths),
  (SELECT count(*) FROM wix_ai_setup_review_items ri WHERE ri.launch_project_id IN (SELECT id FROM proj) AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM paths WHERE path_status = 'ready_for_ai_code_execution'),
  (SELECT count(*) FROM wix_ai_setup_review_items ri WHERE ri.launch_project_id IN (SELECT id FROM proj) AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}' AND ri.status = 'approved'),
  (SELECT count(*) FROM paths WHERE requires_api_key OR requires_publish OR requires_live_webhook),
  (SELECT count(*) FROM wix_ai_implementation_route_decisions rd WHERE rd.launch_project_id IN (SELECT id FROM proj)),
  (SELECT count(*) FROM wix_ai_artifact_review_results ar JOIN wix_ai_implementation_route_decisions rd ON rd.id = ar.route_decision_id WHERE rd.launch_project_id IN (SELECT id FROM proj)),
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
DECLARE ready_paths int; approved_reviews int; unsafe_flags int;
BEGIN
  WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
  paths AS (
    SELECT sp.*
    FROM wix_ai_selected_execution_paths sp
    WHERE sp.launch_project_id IN (SELECT id FROM proj)
      AND sp.raw_context->>'phase' = '{PHASE}'
      AND sp.raw_context->>'source' = '{SOURCE}'
  )
  SELECT
    (SELECT count(*) FROM paths WHERE path_status = 'ready_for_ai_code_execution'),
    (SELECT count(*) FROM wix_ai_setup_review_items ri WHERE ri.launch_project_id IN (SELECT id FROM proj) AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}' AND ri.status = 'approved'),
    (SELECT count(*) FROM paths WHERE requires_api_key OR requires_publish OR requires_live_webhook)
  INTO ready_paths, approved_reviews, unsafe_flags;
  IF ready_paths > 0 THEN RAISE EXCEPTION 'Refusing cleanup: ready_for_ai_code_execution path exists.'; END IF;
  IF approved_reviews > 0 THEN RAISE EXCEPTION 'Refusing cleanup: approved setup review exists.'; END IF;
  IF unsafe_flags > 0 THEN RAISE EXCEPTION 'Refusing cleanup: unsafe setup path flag exists.'; END IF;
END $GUARD$;

DELETE FROM wix_ai_setup_review_items ri
USING launch_projects p
WHERE ri.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND ri.raw_context->>'phase' = '{PHASE}'
  AND ri.raw_context->>'source' = '{SOURCE}';

DELETE FROM wix_ai_selected_execution_paths sp
USING launch_projects p
WHERE sp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND sp.raw_context->>'phase' = '{PHASE}'
  AND sp.raw_context->>'source' = '{SOURCE}';

DELETE FROM wix_ai_setup_availability_checks c
USING launch_projects p
WHERE c.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND c.raw_context->>'phase' = '{PHASE}'
  AND c.raw_context->>'source' = '{SOURCE}';

COMMIT;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up Phase 7.25 Wix setup availability rows. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Wix setup availability cleanup. launch_key={args.launch_key}. Counts only.")
    if not args.real_ok:
        print("Refusing: --real-ok is required, even for cleanup dry-run.")
        return 1
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = [int(x or 0) for x in probe.split("|")[:13]]
    if len(fields) < 13:
        print("Refusing: probe returned no usable result.")
        return 1
    checks, paths, reviews, ready_paths, approved_reviews, unsafe_flags, route_decisions, artifact_reviews, inbound, contacts, send, publish, sent = fields
    if ready_paths or approved_reviews or unsafe_flags:
        print("Refusing cleanup: ready path, approved review, or unsafe setup flag exists.")
        return 1
    if inbound or contacts != 4 or send or publish or sent:
        print("Refusing cleanup: lead/contact/send/publish/communication count is not clean.")
        return 1

    print("intended DB deletions (Phase 7.25 rows only):")
    print(f"  availability checks: {checks}   selected paths: {paths}   setup reviews: {reviews}")
    print(f"  Phase 7.24 route decisions/artifact reviews preserved: {route_decisions}/{artifact_reviews}")
    print("  ignored exports artifacts: UNTOUCHED")
    if not args.apply:
        print("Dry run only. No database or artifact writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(delete_sql(args.launch_key))
    if code != 0:
        print(output)
        return code
    print("Cleanup applied. Phase 7.24 rows and exports artifacts were not deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
