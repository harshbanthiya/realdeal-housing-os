#!/usr/bin/env python3
"""Phase 7.19 — clean up the DLF Westpark Wix staging/preview-site plan rows. Dry-run by default.

Deletes only rows tagged raw_context.phase='7.19' and source='dlf_wix_staging_site_plan_seed'.
It never deletes Phase 7.0-7.18 rows, the approved design output/refinements, the Wix masterplan,
real inbound leads, or contacts.

Refuses if any staging site is marked real_domain_connected, public_indexing_enabled,
page_published, live_form_created, live_webhook_created, or wix_api_call_made, or if any staging
review item has been approved. Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.19"
SOURCE = "dlf_wix_staging_site_plan_seed"
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
sites AS (
  SELECT s.* FROM wix_staging_sites s
  WHERE s.launch_project_id IN (SELECT id FROM proj)
    AND s.raw_context->>'phase' = '{PHASE}' AND s.raw_context->>'source' = '{SOURCE}'
),
items AS (
  SELECT ri.* FROM wix_staging_review_items ri
  WHERE ri.launch_project_id IN (SELECT id FROM proj)
    AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}'
)
SELECT
  (SELECT count(*) FROM sites),
  (SELECT count(*) FROM wix_staging_build_checklist_items c WHERE c.launch_project_id IN (SELECT id FROM proj) AND c.raw_context->>'phase' = '{PHASE}' AND c.raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM wix_staging_qa_checks q WHERE q.launch_project_id IN (SELECT id FROM proj) AND q.raw_context->>'phase' = '{PHASE}' AND q.raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM items),
  (SELECT count(*) FROM sites WHERE real_domain_connected OR public_indexing_enabled OR page_published OR live_form_created OR live_webhook_created OR wix_api_call_made),
  (SELECT count(*) FROM items WHERE status = 'approved');
"""

def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;
DO $GUARD$
DECLARE live int; approved int;
BEGIN
  SELECT count(*) INTO live FROM wix_staging_sites s JOIN launch_projects p ON p.id = s.launch_project_id
    WHERE p.launch_key = {lk} AND s.raw_context->>'phase' = '{PHASE}' AND s.raw_context->>'source' = '{SOURCE}'
      AND (s.real_domain_connected OR s.public_indexing_enabled OR s.page_published
        OR s.live_form_created OR s.live_webhook_created OR s.wix_api_call_made);
  SELECT count(*) INTO approved FROM wix_staging_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id
    WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}'
      AND ri.status = 'approved';
  IF live > 0 THEN RAISE EXCEPTION 'Refusing cleanup: staging site has a live/domain/indexing/publish/api flag set (%).', live; END IF;
  IF approved > 0 THEN RAISE EXCEPTION 'Refusing cleanup: an approved staging review item exists (%).', approved; END IF;
END $GUARD$;

DELETE FROM wix_staging_review_items ri
USING launch_projects p
WHERE ri.launch_project_id = p.id AND p.launch_key = {lk}
  AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}';
DELETE FROM wix_staging_qa_checks q
USING launch_projects p
WHERE q.launch_project_id = p.id AND p.launch_key = {lk}
  AND q.raw_context->>'phase' = '{PHASE}' AND q.raw_context->>'source' = '{SOURCE}';
DELETE FROM wix_staging_build_checklist_items c
USING launch_projects p
WHERE c.launch_project_id = p.id AND p.launch_key = {lk}
  AND c.raw_context->>'phase' = '{PHASE}' AND c.raw_context->>'source' = '{SOURCE}';
DELETE FROM wix_staging_sites s
USING launch_projects p
WHERE s.launch_project_id = p.id AND p.launch_key = {lk}
  AND s.raw_context->>'phase' = '{PHASE}' AND s.raw_context->>'source' = '{SOURCE}';
COMMIT;

SELECT 'staging_sites_remaining', count(*)::text FROM wix_staging_sites s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk} AND s.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'phase_7_18_design_outputs', count(*)::text FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'phase_7_15_wix_blueprints', count(*)::text FROM wix_site_experience_blueprints b JOIN launch_projects p ON p.id = b.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'inbound_leads', count(*)::text FROM inbound_leads
UNION ALL SELECT 'contacts', count(*)::text FROM contacts
ORDER BY 1;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up Phase 7.19 Wix staging-site plan rows. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Westpark Wix staging-site plan cleanup. launch_key={args.launch_key}. Counts only.")
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 6:
        print("Refusing: probe returned no usable result.")
        return 1
    sites, checklist, qa, items, live, approved = (int(x or 0) for x in f[:6])
    if live or approved:
        print("Refusing cleanup: live/domain/indexing/publish/api or approved-review flags are present.")
        print(f"  live/domain/publish/api sites: {live}   approved review items: {approved}")
        return 1

    print("intended DB deletions (Phase 7.19 rows only):")
    print(f"  staging sites: {sites}   checklist items: {checklist}   QA checks: {qa}   review items: {items}")
    print("  Phase 7.0-7.18 rows (approved design, Wix masterplan/specs): UNTOUCHED")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key))
    print("Cleanup applied:" if code == 0 else "Cleanup FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
