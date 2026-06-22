#!/usr/bin/env python3
"""Phase 7.16 — clean up the DLF Westpark Fable UI/UX handoff package rows.

Dry-run by default. Deletes only rows tagged raw_context.phase='7.16' and
source='dlf_fable_uiux_handoff_package'. It never deletes Phase 7.0-7.15 rows,
the Wix UX masterplan, landing/form specs, real inbound leads, or contacts.

Refuses if any package is marked fable_call_made, external_call_made, or has
package_status in approved_for_fable/used_in_fable. Artifact deletion is opt-in
with --delete-artifacts and still requires --real-ok --apply. Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.16"
SOURCE = "dlf_fable_uiux_handoff_package"
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH packages AS (
  SELECT hp.*
  FROM fable_uiux_handoff_packages hp
  JOIN launch_projects p ON p.id = hp.launch_project_id
  WHERE p.launch_key = {lk}
    AND hp.raw_context->>'phase' = '{PHASE}'
    AND hp.raw_context->>'source' = '{SOURCE}'
)
SELECT
  (SELECT count(*) FROM packages),
  (SELECT count(*) FROM fable_uiux_handoff_sections s JOIN packages hp ON hp.id = s.handoff_package_id),
  (SELECT count(*) FROM fable_uiux_handoff_validation_results vr JOIN packages hp ON hp.id = vr.handoff_package_id),
  (SELECT count(*) FROM fable_uiux_handoff_review_items ri JOIN packages hp ON hp.id = ri.handoff_package_id),
  (SELECT count(*) FROM packages WHERE fable_call_made),
  (SELECT count(*) FROM packages WHERE external_call_made),
  (SELECT count(*) FROM packages WHERE package_status IN ('approved_for_fable', 'used_in_fable')),
  (SELECT count(*) FROM packages WHERE concise_prompt_artifact_path IS NOT NULL OR detailed_brief_artifact_path IS NOT NULL);
"""

def artifact_probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT concise_prompt_artifact_path FROM fable_uiux_handoff_packages hp
JOIN launch_projects p ON p.id = hp.launch_project_id
WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}' AND hp.concise_prompt_artifact_path IS NOT NULL
UNION ALL
SELECT detailed_brief_artifact_path FROM fable_uiux_handoff_packages hp
JOIN launch_projects p ON p.id = hp.launch_project_id
WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}' AND hp.detailed_brief_artifact_path IS NOT NULL;
"""

def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;
DO $GUARD$
DECLARE called int; ext int; approved int;
BEGIN
  SELECT count(*) INTO called FROM fable_uiux_handoff_packages hp JOIN launch_projects p ON p.id = hp.launch_project_id
    WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}' AND hp.fable_call_made;
  SELECT count(*) INTO ext FROM fable_uiux_handoff_packages hp JOIN launch_projects p ON p.id = hp.launch_project_id
    WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}' AND hp.external_call_made;
  SELECT count(*) INTO approved FROM fable_uiux_handoff_packages hp JOIN launch_projects p ON p.id = hp.launch_project_id
    WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}' AND hp.package_status IN ('approved_for_fable', 'used_in_fable');
  IF called > 0 THEN RAISE EXCEPTION 'Refusing cleanup: fable_call_made=true package exists.'; END IF;
  IF ext > 0 THEN RAISE EXCEPTION 'Refusing cleanup: external_call_made=true package exists.'; END IF;
  IF approved > 0 THEN RAISE EXCEPTION 'Refusing cleanup: package approved_for_fable/used_in_fable exists.'; END IF;
END $GUARD$;

DELETE FROM fable_uiux_handoff_review_items ri
USING fable_uiux_handoff_packages hp, launch_projects p
WHERE ri.handoff_package_id = hp.id AND hp.launch_project_id = p.id AND p.launch_key = {lk}
  AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}';
DELETE FROM fable_uiux_handoff_validation_results vr
USING fable_uiux_handoff_packages hp, launch_projects p
WHERE vr.handoff_package_id = hp.id AND hp.launch_project_id = p.id AND p.launch_key = {lk}
  AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}';
DELETE FROM fable_uiux_handoff_sections s
USING fable_uiux_handoff_packages hp, launch_projects p
WHERE s.handoff_package_id = hp.id AND hp.launch_project_id = p.id AND p.launch_key = {lk}
  AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}';
DELETE FROM fable_uiux_handoff_packages hp
USING launch_projects p
WHERE hp.launch_project_id = p.id AND p.launch_key = {lk}
  AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}';
COMMIT;

SELECT 'handoff_packages_remaining', count(*)::text FROM fable_uiux_handoff_packages hp JOIN launch_projects p ON p.id = hp.launch_project_id WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'phase_7_15_blueprints', count(*)::text FROM wix_site_experience_blueprints seb JOIN launch_projects p ON p.id = seb.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'phase_7_14_wix_build_packages', count(*)::text FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk}
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
    exports_root = (PROJECT_ROOT / "exports" / "fable_handoffs").resolve()
    for rel in output.splitlines():
        if not rel.strip():
            continue
        path = PROJECT_ROOT / rel.strip()
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(exports_root):
                print("Refusing artifact delete outside exports/fable_handoffs.")
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
    parser = argparse.ArgumentParser(description="Clean up Phase 7.16 Fable handoff package rows. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--delete-artifacts", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Westpark Fable handoff cleanup. launch_key={args.launch_key}. Counts only.")
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 8:
        print("Refusing: probe returned no usable result.")
        return 1
    packages, sections, validations, reviews, called, ext, approved, artifacts = (int(x or 0) for x in fields[:8])
    if called or ext or approved:
        print("Refusing cleanup: called/external/approved package flags are present.")
        print(f"  fable_call_made: {called}   external_call_made: {ext}   approved/used_in_fable: {approved}")
        return 1

    print("intended DB deletions (Phase 7.16 rows only):")
    print(f"  handoff packages: {packages}   sections: {sections}   validations: {validations}   review items: {reviews}")
    print("  Phase 7.0-7.15 rows (Wix masterplan, build packages, specs): UNTOUCHED")
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
