#!/usr/bin/env python3
"""Phase 7.17 — clean up the DLF Westpark Fable/Gemini design output capture rows.

Dry-run by default. Deletes only rows tagged raw_context.phase='7.17' and
source='fable_gemini_design_output_capture'. It never deletes Phase 7.0-7.16 rows,
the Fable handoff package, the Wix masterplan/specs, real inbound leads, or contacts.

Refuses if any captured output is output_status='accepted_direction', any second-opinion
review is review_status in accepted_guidance/partially_accepted, any refinement action is
action_status='accepted', or any row is marked external_call_made. Raw Fable/Gemini
artifacts under exports/ are preserved unless --delete-artifacts is given explicitly (and
even then only files under exports/, still requiring --real-ok --apply). Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORTS_ROOT = PROJECT_ROOT / "exports"
PHASE = "7.17"
SOURCE = "fable_gemini_design_output_capture"
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH outputs AS (
  SELECT o.* FROM fable_design_outputs o
  JOIN launch_projects p ON p.id = o.launch_project_id
  WHERE p.launch_key = {lk}
    AND o.raw_context->>'phase' = '{PHASE}' AND o.raw_context->>'source' = '{SOURCE}'
),
reviews AS (
  SELECT r.* FROM design_second_opinion_reviews r
  JOIN launch_projects p ON p.id = r.launch_project_id
  WHERE p.launch_key = {lk}
    AND r.raw_context->>'phase' = '{PHASE}' AND r.raw_context->>'source' = '{SOURCE}'
),
actions AS (
  SELECT a.* FROM design_refinement_actions a
  JOIN launch_projects p ON p.id = a.launch_project_id
  WHERE p.launch_key = {lk}
    AND a.raw_context->>'phase' = '{PHASE}' AND a.raw_context->>'source' = '{SOURCE}'
),
items AS (
  SELECT ri.* FROM fable_design_review_items ri
  JOIN launch_projects p ON p.id = ri.launch_project_id
  WHERE p.launch_key = {lk}
    AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}'
)
SELECT
  (SELECT count(*) FROM outputs),
  (SELECT count(*) FROM reviews),
  (SELECT count(*) FROM actions),
  (SELECT count(*) FROM items),
  (SELECT count(*) FROM outputs WHERE output_status = 'accepted_direction'),
  (SELECT count(*) FROM reviews WHERE review_status IN ('accepted_guidance', 'partially_accepted')),
  (SELECT count(*) FROM actions WHERE action_status = 'accepted'),
  (SELECT count(*) FROM outputs WHERE external_call_made)
    + (SELECT count(*) FROM reviews WHERE external_call_made),
  (SELECT count(*) FROM outputs WHERE raw_artifact_path IS NOT NULL OR preview_artifact_path IS NOT NULL)
    + (SELECT count(*) FROM reviews WHERE raw_artifact_path IS NOT NULL);
"""

def artifact_probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT raw_artifact_path FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id
WHERE p.launch_key = {lk} AND o.raw_context->>'phase' = '{PHASE}' AND o.raw_context->>'source' = '{SOURCE}' AND o.raw_artifact_path IS NOT NULL
UNION ALL
SELECT preview_artifact_path FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id
WHERE p.launch_key = {lk} AND o.raw_context->>'phase' = '{PHASE}' AND o.raw_context->>'source' = '{SOURCE}' AND o.preview_artifact_path IS NOT NULL
UNION ALL
SELECT raw_artifact_path FROM design_second_opinion_reviews r JOIN launch_projects p ON p.id = r.launch_project_id
WHERE p.launch_key = {lk} AND r.raw_context->>'phase' = '{PHASE}' AND r.raw_context->>'source' = '{SOURCE}' AND r.raw_artifact_path IS NOT NULL;
"""

def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;
DO $GUARD$
DECLARE accepted_out int; accepted_rev int; accepted_act int; ext int;
BEGIN
  SELECT count(*) INTO accepted_out FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id
    WHERE p.launch_key = {lk} AND o.raw_context->>'phase' = '{PHASE}' AND o.raw_context->>'source' = '{SOURCE}' AND o.output_status = 'accepted_direction';
  SELECT count(*) INTO accepted_rev FROM design_second_opinion_reviews r JOIN launch_projects p ON p.id = r.launch_project_id
    WHERE p.launch_key = {lk} AND r.raw_context->>'phase' = '{PHASE}' AND r.raw_context->>'source' = '{SOURCE}' AND r.review_status IN ('accepted_guidance', 'partially_accepted');
  SELECT count(*) INTO accepted_act FROM design_refinement_actions a JOIN launch_projects p ON p.id = a.launch_project_id
    WHERE p.launch_key = {lk} AND a.raw_context->>'phase' = '{PHASE}' AND a.raw_context->>'source' = '{SOURCE}' AND a.action_status = 'accepted';
  SELECT (SELECT count(*) FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id
            WHERE p.launch_key = {lk} AND o.raw_context->>'phase' = '{PHASE}' AND o.raw_context->>'source' = '{SOURCE}' AND o.external_call_made)
       + (SELECT count(*) FROM design_second_opinion_reviews r JOIN launch_projects p ON p.id = r.launch_project_id
            WHERE p.launch_key = {lk} AND r.raw_context->>'phase' = '{PHASE}' AND r.raw_context->>'source' = '{SOURCE}' AND r.external_call_made)
    INTO ext;
  IF accepted_out > 0 THEN RAISE EXCEPTION 'Refusing cleanup: output accepted_direction exists.'; END IF;
  IF accepted_rev > 0 THEN RAISE EXCEPTION 'Refusing cleanup: second-opinion review accepted_guidance/partially_accepted exists.'; END IF;
  IF accepted_act > 0 THEN RAISE EXCEPTION 'Refusing cleanup: refinement action accepted exists.'; END IF;
  IF ext > 0 THEN RAISE EXCEPTION 'Refusing cleanup: external_call_made row exists.'; END IF;
END $GUARD$;

DELETE FROM fable_design_review_items ri
USING launch_projects p
WHERE ri.launch_project_id = p.id AND p.launch_key = {lk}
  AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}';
DELETE FROM design_refinement_actions a
USING launch_projects p
WHERE a.launch_project_id = p.id AND p.launch_key = {lk}
  AND a.raw_context->>'phase' = '{PHASE}' AND a.raw_context->>'source' = '{SOURCE}';
DELETE FROM design_second_opinion_reviews r
USING launch_projects p
WHERE r.launch_project_id = p.id AND p.launch_key = {lk}
  AND r.raw_context->>'phase' = '{PHASE}' AND r.raw_context->>'source' = '{SOURCE}';
DELETE FROM fable_design_outputs o
USING launch_projects p
WHERE o.launch_project_id = p.id AND p.launch_key = {lk}
  AND o.raw_context->>'phase' = '{PHASE}' AND o.raw_context->>'source' = '{SOURCE}';
COMMIT;

SELECT 'fable_design_outputs_remaining', count(*)::text FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id WHERE p.launch_key = {lk} AND o.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'second_opinion_reviews_remaining', count(*)::text FROM design_second_opinion_reviews r JOIN launch_projects p ON p.id = r.launch_project_id WHERE p.launch_key = {lk} AND r.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'refinement_actions_remaining', count(*)::text FROM design_refinement_actions a JOIN launch_projects p ON p.id = a.launch_project_id WHERE p.launch_key = {lk} AND a.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'review_items_remaining', count(*)::text FROM fable_design_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'phase_7_16_fable_handoff_packages', count(*)::text FROM fable_uiux_handoff_packages hp JOIN launch_projects p ON p.id = hp.launch_project_id WHERE p.launch_key = {lk}
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
    exports_root = EXPORTS_ROOT.resolve()
    for rel in output.splitlines():
        if not rel.strip():
            continue
        path = PROJECT_ROOT / rel.strip()
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(exports_root):
                print("Refusing artifact delete outside exports/.")
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
    parser = argparse.ArgumentParser(description="Clean up Phase 7.17 Fable/Gemini design capture rows. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--delete-artifacts", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Westpark Fable/Gemini design capture cleanup. launch_key={args.launch_key}. Counts only.")
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 9:
        print("Refusing: probe returned no usable result.")
        return 1
    outputs, reviews, actions, items, acc_out, acc_rev, acc_act, ext, artifacts = (int(x or 0) for x in fields[:9])
    if acc_out or acc_rev or acc_act or ext:
        print("Refusing cleanup: accepted/external rows are present.")
        print(f"  accepted_direction outputs: {acc_out}   accepted reviews: {acc_rev}   "
              f"accepted actions: {acc_act}   external_call_made: {ext}")
        return 1

    print("intended DB deletions (Phase 7.17 rows only):")
    print(f"  fable_design_outputs: {outputs}   second_opinion_reviews: {reviews}   "
          f"refinement_actions: {actions}   review_items: {items}")
    print("  Phase 7.0-7.16 rows (Fable handoff package, Wix masterplan/specs): UNTOUCHED")
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
