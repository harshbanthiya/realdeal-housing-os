#!/usr/bin/env python3
"""Phase 7.11 — clean up DLF n8n build package tracking rows.

Dry-run by default. Deletes only rows tagged raw_context.phase='7.11' and
source='dlf_n8n_build_package'. It never deletes Phase 7.4 n8n blueprints,
Phase 7.10 test lead rows, real inbound leads, contacts, or live n8n objects.

Artifact deletion is opt-in with --delete-artifacts and still requires
--real-ok --apply. Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.11"
SOURCE = "dlf_n8n_build_package"
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH packages AS (
  SELECT bp.*
  FROM launch_n8n_build_packages bp
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk}
    AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}'
)
SELECT
  (SELECT count(*) FROM packages),
  (SELECT count(*) FROM launch_n8n_build_validation_results vr JOIN packages bp ON bp.id = vr.build_package_id),
  (SELECT count(*) FROM launch_n8n_build_review_items ri JOIN packages bp ON bp.id = ri.build_package_id),
  (SELECT count(*) FROM packages WHERE workflow_created_in_n8n),
  (SELECT count(*) FROM packages WHERE activation_requested),
  (SELECT count(*) FROM packages WHERE package_status = 'approved_for_manual_import'),
  (SELECT count(*) FROM packages WHERE artifact_path IS NOT NULL);
"""

def artifact_probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT artifact_path
FROM launch_n8n_build_packages bp
JOIN launch_projects p ON p.id = bp.launch_project_id
WHERE p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}'
  AND bp.artifact_path IS NOT NULL;
"""

def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;
DO $GUARD$
DECLARE created int; activated int; approved int;
BEGIN
  SELECT count(*) INTO created
  FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}' AND bp.workflow_created_in_n8n;
  SELECT count(*) INTO activated
  FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}' AND bp.activation_requested;
  SELECT count(*) INTO approved
  FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}' AND bp.package_status = 'approved_for_manual_import';
  IF created > 0 THEN RAISE EXCEPTION 'Refusing cleanup: workflow_created_in_n8n=true package exists.'; END IF;
  IF activated > 0 THEN RAISE EXCEPTION 'Refusing cleanup: activation_requested=true package exists.'; END IF;
  IF approved > 0 THEN RAISE EXCEPTION 'Refusing cleanup: package approved_for_manual_import exists.'; END IF;
END $GUARD$;

DELETE FROM launch_n8n_build_review_items ri
USING launch_n8n_build_packages bp, launch_projects p
WHERE ri.build_package_id = bp.id
  AND bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';

DELETE FROM launch_n8n_build_validation_results vr
USING launch_n8n_build_packages bp, launch_projects p
WHERE vr.build_package_id = bp.id
  AND bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';

DELETE FROM launch_n8n_build_packages bp
USING launch_projects p
WHERE bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';
COMMIT;

SELECT 'build_packages_remaining', count(*)::text FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'phase_7_4_blueprints', count(*)::text FROM launch_n8n_workflow_blueprints wb JOIN launch_projects p ON p.id = wb.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'phase_7_10_payloads', count(*)::text FROM launch_test_lead_payloads t JOIN launch_projects p ON p.id = t.launch_project_id WHERE p.launch_key = {lk} AND t.raw_context->>'phase' = '7.10'
UNION ALL SELECT 'inbound_leads', count(*)::text FROM inbound_leads
UNION ALL SELECT 'contacts', count(*)::text FROM contacts
ORDER BY 1;
"""

def delete_artifacts(launch_key: str) -> int:
    code, output = run_psql(artifact_probe_sql(launch_key))
    if code != 0:
        print(output)
        return code
    deleted = 0
    for rel in output.splitlines():
        if not rel.strip():
            continue
        path = PROJECT_ROOT / rel.strip()
        try:
            resolved = path.resolve()
            exports_root = (PROJECT_ROOT / "exports" / "n8n_templates").resolve()
            if not resolved.is_relative_to(exports_root):
                print("Refusing artifact delete outside exports/n8n_templates.")
                return 1
            if resolved.exists():
                resolved.unlink()
                deleted += 1
        except OSError as exc:
            print(f"Artifact delete failed: {exc}")
            return 1
    print(f"artifacts_deleted: {deleted}")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up Phase 7.11 DLF n8n build package rows. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--delete-artifacts", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF n8n build package cleanup. launch_key={args.launch_key}. Counts only.")
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 7:
        print("Refusing: probe returned no usable result.")
        return 1
    packages, validations, reviews, created, activated, approved, artifacts = (int(x or 0) for x in fields[:7])
    if created or activated or approved:
        print("Refusing cleanup: created/activation/approved package flags are present.")
        print(f"  workflow_created_in_n8n: {created}   activation_requested: {activated}   approved_for_manual_import: {approved}")
        return 1

    print("intended DB deletions (Phase 7.11 rows only):")
    print(f"  build packages: {packages}   validation results: {validations}   review items: {reviews}")
    print("  Phase 7.4 blueprints and Phase 7.10 test rows: UNTOUCHED")
    print(f"  artifacts_found: {artifacts}   artifact_delete_requested: {str(args.delete_artifacts).lower()}")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database or artifact writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    if args.delete_artifacts:
        code = delete_artifacts(args.launch_key)
        if code != 0:
            return code

    code, output = run_psql(apply_sql(args.launch_key))
    print("Cleanup applied:" if code == 0 else "Cleanup FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
