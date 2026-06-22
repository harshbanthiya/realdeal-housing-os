#!/usr/bin/env python3
"""Phase 7.21 — clean up the Wix API permission/capability map rows. Dry-run by default.

Deletes only rows tagged raw_context.phase='7.21' and source='wix_api_permission_capability_map_seed'.
It never deletes Phase 7.0-7.20 rows, stores or reads secrets, or calls any API.

Refuses if any key profile is active, any external_call_allowed=true, any secret_value_stored=true,
any publish-permission or send-permission is marked allowed, or any review item is approved. Counts
only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.21"
SOURCE = "wix_api_permission_capability_map_seed"
def probe_sql() -> str:
    return f"""
SELECT
  (SELECT count(*) FROM wix_api_permission_catalog WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM wix_api_integration_use_cases WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM wix_api_permission_review_items WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND profile_status = 'active'),
  (SELECT count(*) FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND external_call_allowed),
  (SELECT count(*) FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND secret_value_stored),
  (SELECT count(*) FROM wix_api_integration_use_cases WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND can_publish AND use_case_status = 'approved_for_staging'),
  (SELECT count(*) FROM wix_api_integration_use_cases WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND can_send_messages AND use_case_status = 'approved_for_staging'),
  (SELECT count(*) FROM wix_api_permission_review_items WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND status = 'approved');
"""

def apply_sql() -> str:
    return f"""
BEGIN;
DO $GUARD$
DECLARE active int; ext int; sec int; pubperm int; sendperm int; approved int;
BEGIN
  SELECT count(*) INTO active FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND profile_status = 'active';
  SELECT count(*) INTO ext FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND external_call_allowed;
  SELECT count(*) INTO sec FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND secret_value_stored;
  SELECT count(*) INTO pubperm FROM wix_api_integration_use_cases WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND can_publish AND use_case_status = 'approved_for_staging';
  SELECT count(*) INTO sendperm FROM wix_api_integration_use_cases WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND can_send_messages AND use_case_status = 'approved_for_staging';
  SELECT count(*) INTO approved FROM wix_api_permission_review_items WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' AND status = 'approved';
  IF active > 0 THEN RAISE EXCEPTION 'Refusing cleanup: an active key profile exists.'; END IF;
  IF ext > 0 THEN RAISE EXCEPTION 'Refusing cleanup: a key profile has external_call_allowed.'; END IF;
  IF sec > 0 THEN RAISE EXCEPTION 'Refusing cleanup: a key profile reports secret_value_stored.'; END IF;
  IF pubperm > 0 THEN RAISE EXCEPTION 'Refusing cleanup: a publish permission is marked allowed.'; END IF;
  IF sendperm > 0 THEN RAISE EXCEPTION 'Refusing cleanup: a send permission is marked allowed.'; END IF;
  IF approved > 0 THEN RAISE EXCEPTION 'Refusing cleanup: an approved review item exists.'; END IF;
END $GUARD$;

DELETE FROM wix_api_permission_review_items WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}';
DELETE FROM wix_api_integration_use_cases WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}';
DELETE FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}';
DELETE FROM wix_api_permission_catalog WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}';
COMMIT;

SELECT 'permission_catalog_remaining', count(*)::text FROM wix_api_permission_catalog WHERE raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'use_cases_remaining', count(*)::text FROM wix_api_integration_use_cases WHERE raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'key_profiles_remaining', count(*)::text FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'review_items_remaining', count(*)::text FROM wix_api_permission_review_items WHERE raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'phase_7_19_staging_sites', count(*)::text FROM wix_staging_sites
UNION ALL SELECT 'inbound_leads', count(*)::text FROM inbound_leads
UNION ALL SELECT 'contacts', count(*)::text FROM contacts
ORDER BY 1;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up Phase 7.21 Wix API capability map rows. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print("Wix API permission/capability map cleanup. Counts only.")
    code, probe = run_psql(probe_sql())
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 10:
        print("Refusing: probe returned no usable result.")
        return 1
    catalog, use_cases, profiles, reviews, active, ext, sec, pubperm, sendperm, approved = (int(x or 0) for x in f[:10])
    if active or ext or sec or pubperm or sendperm or approved:
        print("Refusing cleanup: active/external/secret/publish/send/approved flags are present.")
        print(f"  active_profiles: {active}   external_call_allowed: {ext}   secret_value_stored: {sec}   "
              f"publish_allowed: {pubperm}   send_allowed: {sendperm}   approved_reviews: {approved}")
        return 1

    print("intended DB deletions (Phase 7.21 rows only):")
    print(f"  permission catalog: {catalog}   use cases: {use_cases}   key profiles: {profiles}   review items: {reviews}")
    print("  Phase 7.0-7.20 rows (staging plan, build tracking, design): UNTOUCHED")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql())
    print("Cleanup applied:" if code == 0 else "Cleanup FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
