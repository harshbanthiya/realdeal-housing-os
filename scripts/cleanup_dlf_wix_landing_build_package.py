#!/usr/bin/env python3
"""Phase 7.14 — clean up DLF Wix landing/form build package tracking rows.

Dry-run by default. Deletes only rows tagged raw_context.phase='7.14' and
source='dlf_wix_landing_build_package'. It never deletes Phase 7.0-7.13 rows,
landing/form specs, field mappings, content pillars, real inbound leads,
contacts, or any live Wix object.

Refuses if any package is marked wix_page_created, wix_page_published,
live_form_created, or has package_status in built_in_wix/published. Artifact
deletion is opt-in with --delete-artifacts and still requires --real-ok --apply.
Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.14"
SOURCE = "dlf_wix_landing_build_package"
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH packages AS (
  SELECT bp.*
  FROM launch_wix_build_packages bp
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk}
    AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}'
)
SELECT
  (SELECT count(*) FROM packages),
  (SELECT count(*) FROM launch_wix_build_validation_results vr JOIN packages bp ON bp.id = vr.build_package_id),
  (SELECT count(*) FROM launch_wix_build_review_items ri JOIN packages bp ON bp.id = ri.build_package_id),
  (SELECT count(*) FROM packages WHERE wix_page_created),
  (SELECT count(*) FROM packages WHERE wix_page_published),
  (SELECT count(*) FROM packages WHERE live_form_created),
  (SELECT count(*) FROM packages WHERE package_status IN ('built_in_wix', 'published')),
  (SELECT count(*) FROM packages WHERE artifact_path IS NOT NULL);
"""

def artifact_probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT artifact_path
FROM launch_wix_build_packages bp
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
DECLARE created int; published int; liveform int; built int;
BEGIN
  SELECT count(*) INTO created
  FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}' AND bp.wix_page_created;
  SELECT count(*) INTO published
  FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}' AND bp.wix_page_published;
  SELECT count(*) INTO liveform
  FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}' AND bp.live_form_created;
  SELECT count(*) INTO built
  FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}' AND bp.package_status IN ('built_in_wix', 'published');
  IF created > 0 THEN RAISE EXCEPTION 'Refusing cleanup: wix_page_created=true package exists.'; END IF;
  IF published > 0 THEN RAISE EXCEPTION 'Refusing cleanup: wix_page_published=true package exists.'; END IF;
  IF liveform > 0 THEN RAISE EXCEPTION 'Refusing cleanup: live_form_created=true package exists.'; END IF;
  IF built > 0 THEN RAISE EXCEPTION 'Refusing cleanup: package status built_in_wix/published exists.'; END IF;
END $GUARD$;

DELETE FROM launch_wix_build_review_items ri
USING launch_wix_build_packages bp, launch_projects p
WHERE ri.build_package_id = bp.id
  AND bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';

DELETE FROM launch_wix_build_validation_results vr
USING launch_wix_build_packages bp, launch_projects p
WHERE vr.build_package_id = bp.id
  AND bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';

DELETE FROM launch_wix_build_packages bp
USING launch_projects p
WHERE bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';
COMMIT;

SELECT 'wix_build_packages_remaining', count(*)::text FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'landing_page_specs', count(*)::text FROM launch_landing_page_specs s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'lead_capture_forms', count(*)::text FROM launch_lead_capture_forms f JOIN launch_projects p ON p.id = f.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'field_mappings', count(*)::text FROM launch_lead_field_mappings m JOIN launch_projects p ON p.id = m.launch_project_id WHERE p.launch_key = {lk}
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
            exports_root = (PROJECT_ROOT / "exports" / "wix_build_packages").resolve()
            if not resolved.is_relative_to(exports_root):
                print("Refusing artifact delete outside exports/wix_build_packages.")
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
    parser = argparse.ArgumentParser(description="Clean up Phase 7.14 DLF Wix build package rows. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--delete-artifacts", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Wix build package cleanup. launch_key={args.launch_key}. Counts only.")
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 8:
        print("Refusing: probe returned no usable result.")
        return 1
    packages, validations, reviews, created, published, liveform, built, artifacts = (int(x or 0) for x in fields[:8])
    if created or published or liveform or built:
        print("Refusing cleanup: built/published/live package flags are present.")
        print(f"  wix_page_created: {created}   wix_page_published: {published}   live_form_created: {liveform}   built/published_status: {built}")
        return 1

    print("intended DB deletions (Phase 7.14 rows only):")
    print(f"  build packages: {packages}   validation results: {validations}   review items: {reviews}")
    print("  Phase 7.0-7.13 rows, landing/form specs, field mappings, content pillars: UNTOUCHED")
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
