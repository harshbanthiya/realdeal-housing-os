#!/usr/bin/env python3
"""Phase 7.15 — clean up the DLF Wix UX/SEO/integration masterplan seed.

Dry-run by default. Deletes only rows tagged raw_context.phase='7.15' and
source='dlf_wix_ux_integration_masterplan_seed'. It never deletes Phase 7.0-7.14
rows, landing/form specs, field mappings, content pillars, Wix build packages,
real inbound leads, or contacts.

Refuses if any masterplan row indicates real activity: an integration with
external_call_allowed=true or readiness_status in active/connected_manually, a
page with publish_enabled=true, or any review item already approved. Counts only.
Writing requires BOTH --real-ok and --apply.
"""

from __future__ import annotations
from _db import lit, read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.15"
SOURCE = "dlf_wix_ux_integration_masterplan_seed"
def probe_sql(launch_key: str) -> str:
    lk = lit(launch_key)
    p = f"raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}'"
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk})
SELECT
  (SELECT count(*) FROM wix_site_experience_blueprints seb JOIN proj ON proj.id = seb.launch_project_id WHERE {p}),
  (SELECT count(*) FROM wix_page_blueprints pb JOIN proj ON proj.id = pb.launch_project_id WHERE {p}),
  (SELECT count(*) FROM wix_integration_readiness_items iri JOIN proj ON proj.id = iri.launch_project_id WHERE {p}),
  (SELECT count(*) FROM wix_design_component_specs dcs JOIN proj ON proj.id = dcs.launch_project_id WHERE {p}),
  (SELECT count(*) FROM wix_ux_review_items ri JOIN proj ON proj.id = ri.launch_project_id WHERE {p}),
  (SELECT count(*) FROM wix_integration_readiness_items iri JOIN proj ON proj.id = iri.launch_project_id WHERE {p} AND iri.external_call_allowed),
  (SELECT count(*) FROM wix_integration_readiness_items iri JOIN proj ON proj.id = iri.launch_project_id WHERE {p} AND iri.readiness_status IN ('active','connected_manually')),
  (SELECT count(*) FROM wix_page_blueprints pb JOIN proj ON proj.id = pb.launch_project_id WHERE {p} AND pb.publish_enabled),
  (SELECT count(*) FROM wix_ux_review_items ri JOIN proj ON proj.id = ri.launch_project_id WHERE {p} AND ri.status = 'approved');
"""

def _tag(alias: str) -> str:
    return f"{alias}.raw_context->>'phase' = '{PHASE}' AND {alias}.raw_context->>'source' = '{SOURCE}'"

def apply_sql(launch_key: str) -> str:
    lk = lit(launch_key)
    return f"""
BEGIN;
DO $GUARD$
DECLARE ext int; act int; pub int; appr int;
BEGIN
  SELECT count(*) INTO ext FROM wix_integration_readiness_items iri JOIN launch_projects p ON p.id = iri.launch_project_id
    WHERE p.launch_key = {lk} AND {_tag('iri')} AND iri.external_call_allowed;
  SELECT count(*) INTO act FROM wix_integration_readiness_items iri JOIN launch_projects p ON p.id = iri.launch_project_id
    WHERE p.launch_key = {lk} AND {_tag('iri')} AND iri.readiness_status IN ('active','connected_manually');
  SELECT count(*) INTO pub FROM wix_page_blueprints pb JOIN launch_projects p ON p.id = pb.launch_project_id
    WHERE p.launch_key = {lk} AND {_tag('pb')} AND pb.publish_enabled;
  SELECT count(*) INTO appr FROM wix_ux_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id
    WHERE p.launch_key = {lk} AND {_tag('ri')} AND ri.status = 'approved';
  IF ext > 0 THEN RAISE EXCEPTION 'Refusing cleanup: integration external_call_allowed=true exists.'; END IF;
  IF act > 0 THEN RAISE EXCEPTION 'Refusing cleanup: integration active/connected exists.'; END IF;
  IF pub > 0 THEN RAISE EXCEPTION 'Refusing cleanup: page publish_enabled=true exists.'; END IF;
  IF appr > 0 THEN RAISE EXCEPTION 'Refusing cleanup: an approved review item exists.'; END IF;
END $GUARD$;

DELETE FROM wix_ux_review_items ri USING launch_projects p
WHERE ri.launch_project_id = p.id AND p.launch_key = {lk} AND {_tag('ri')};
DELETE FROM wix_design_component_specs dcs USING launch_projects p
WHERE dcs.launch_project_id = p.id AND p.launch_key = {lk} AND {_tag('dcs')};
DELETE FROM wix_integration_readiness_items iri USING launch_projects p
WHERE iri.launch_project_id = p.id AND p.launch_key = {lk} AND {_tag('iri')};
DELETE FROM wix_page_blueprints pb USING launch_projects p
WHERE pb.launch_project_id = p.id AND p.launch_key = {lk} AND {_tag('pb')};
DELETE FROM wix_site_experience_blueprints seb USING launch_projects p
WHERE seb.launch_project_id = p.id AND p.launch_key = {lk} AND {_tag('seb')};
COMMIT;

SELECT 'masterplan_rows_remaining', (
  (SELECT count(*) FROM wix_site_experience_blueprints seb JOIN launch_projects p ON p.id = seb.launch_project_id WHERE p.launch_key = {lk} AND {_tag('seb')})
  + (SELECT count(*) FROM wix_page_blueprints pb JOIN launch_projects p ON p.id = pb.launch_project_id WHERE p.launch_key = {lk} AND {_tag('pb')})
  + (SELECT count(*) FROM wix_integration_readiness_items iri JOIN launch_projects p ON p.id = iri.launch_project_id WHERE p.launch_key = {lk} AND {_tag('iri')})
  + (SELECT count(*) FROM wix_design_component_specs dcs JOIN launch_projects p ON p.id = dcs.launch_project_id WHERE p.launch_key = {lk} AND {_tag('dcs')})
  + (SELECT count(*) FROM wix_ux_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND {_tag('ri')})
)::text
UNION ALL SELECT 'wix_build_packages_phase_7_14', count(*)::text FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'landing_page_specs', count(*)::text FROM launch_landing_page_specs s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk}
UNION ALL SELECT 'inbound_leads', count(*)::text FROM inbound_leads
UNION ALL SELECT 'contacts', count(*)::text FROM contacts
ORDER BY 1;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up Phase 7.15 Wix masterplan rows. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Wix UX/SEO/integration masterplan cleanup. launch_key={args.launch_key}. Counts only.")
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 9:
        print("Refusing: probe returned no usable result.")
        return 1
    seb, pages, integ, comps, reviews, ext, act, pub, appr = (int(x or 0) for x in fields[:9])
    if ext or act or pub or appr:
        print("Refusing cleanup: real-activity flags present.")
        print(f"  external_call_allowed: {ext}   active/connected: {act}   publish_enabled: {pub}   approved_reviews: {appr}")
        return 1

    print("intended DB deletions (Phase 7.15 rows only):")
    print(f"  site experience blueprints: {seb}   page blueprints: {pages}   integration items: {integ}")
    print(f"  design components: {comps}   review items: {reviews}")
    print("  Phase 7.0-7.14 rows, landing/form specs, field mappings, Wix build packages: UNTOUCHED")

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
