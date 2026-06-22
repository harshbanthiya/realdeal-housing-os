#!/usr/bin/env python3
"""Phase 7.8 — revert the DLF consent/privacy PROCESS review. Dry-run by default.

Undoes ONLY what review_dlf_consent_privacy_readiness.py wrote, identified by its raw_context
markers (raw_context.phase = '7.8'):
  - deletes the Phase 7.8 launch_consent_privacy_review_log rows;
  - restores the lead_privacy_reviewed and consent_ready readiness checks to their prior status;
  - restores the whatsapp/email permission review items to their prior status (clearing the
    reviewer/notes) and removes the phase markers.

It REFUSES if any send/publish flag became true after the review. It never touches contacts,
channel_permissions, leads, or messages.

Writing requires BOTH --real-ok and --apply. Counts only; never prints contact values.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT
  (SELECT count(*) FROM launch_consent_privacy_review_log lg JOIN launch_projects p ON p.id = lg.launch_project_id
     WHERE p.launch_key = {lk} AND lg.raw_context->>'phase' = '7.8'),
  (SELECT count(*) FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id
     WHERE p.launch_key = {lk} AND r.check_type IN ('lead_privacy_reviewed','consent_ready') AND r.raw_context->>'phase' = '7.8'),
  (SELECT count(*) FROM launch_contact_permission_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id
     WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '7.8'),
  (SELECT safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk});
"""

def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;
-- Refuse if anything was activated after the review.
DO $GUARD$
DECLARE se int; pe int;
BEGIN
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN launch_projects p ON p.id = lc.launch_project_id WHERE p.launch_key = {lk} AND lc.send_enabled)
    + (SELECT count(*) FROM launch_message_templates m JOIN launch_projects p ON p.id = m.launch_project_id WHERE p.launch_key = {lk} AND m.send_enabled)
    + (SELECT count(*) FROM launch_campaign_calendar cc JOIN launch_projects p ON p.id = cc.launch_project_id WHERE p.launch_key = {lk} AND cc.send_enabled)
  INTO se;
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN launch_projects p ON p.id = lc.launch_project_id WHERE p.launch_key = {lk} AND lc.publish_enabled)
    + (SELECT count(*) FROM launch_landing_page_specs s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk} AND s.publish_enabled)
    + (SELECT count(*) FROM launch_lead_capture_forms f JOIN launch_projects p ON p.id = f.launch_project_id WHERE p.launch_key = {lk} AND f.publish_enabled)
    + (SELECT count(*) FROM launch_social_content_drafts sc JOIN launch_projects p ON p.id = sc.launch_project_id WHERE p.launch_key = {lk} AND sc.publish_enabled)
  INTO pe;
  IF se > 0 OR pe > 0 THEN
    RAISE EXCEPTION 'Refusing revert: send/publish was enabled after review (send=%, publish=%).', se, pe;
  END IF;
END $GUARD$;

-- 1. Restore readiness checks (lead_privacy_reviewed, consent_ready).
UPDATE launch_readiness_checks r SET
  check_status = COALESCE(r.raw_context->>'phase_7_8_prev_status', 'pending'),
  safe_summary = NULL,
  raw_context = r.raw_context - 'phase' - 'phase_7_8_action' - 'phase_7_8_prev_status',
  updated_at = now()
FROM launch_projects p
WHERE p.id = r.launch_project_id AND p.launch_key = {lk}
  AND r.check_type IN ('lead_privacy_reviewed','consent_ready') AND r.raw_context->>'phase' = '7.8';

-- 2. Restore permission review items.
UPDATE launch_contact_permission_review_items ri SET
  status = COALESCE(ri.raw_context->>'phase_7_8_prev_status', 'pending'),
  reviewed_by = NULL, reviewed_at = NULL, decision_notes = NULL,
  raw_context = ri.raw_context - 'phase' - 'phase_7_8_action' - 'phase_7_8_prev_status',
  updated_at = now()
FROM launch_projects p
WHERE p.id = ri.launch_project_id AND p.launch_key = {lk} AND ri.raw_context->>'phase' = '7.8';

-- 3. Delete the Phase 7.8 review-log rows.
DELETE FROM launch_consent_privacy_review_log lg
USING launch_projects p
WHERE p.id = lg.launch_project_id AND p.launch_key = {lk} AND lg.raw_context->>'phase' = '7.8';
COMMIT;

SELECT 'log_rows_phase_7_8_remaining', count(*)::text FROM launch_consent_privacy_review_log lg
  JOIN launch_projects p ON p.id = lg.launch_project_id WHERE p.launch_key = {lk} AND lg.raw_context->>'phase' = '7.8'
UNION ALL SELECT 'lead_privacy_reviewed', check_status FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id WHERE p.launch_key = {lk} AND r.check_type = 'lead_privacy_reviewed'
UNION ALL SELECT 'consent_ready', check_status FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id WHERE p.launch_key = {lk} AND r.check_type = 'consent_ready'
UNION ALL SELECT 'permission_reviews_phase_7_8_remaining', count(*)::text FROM launch_contact_permission_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '7.8'
UNION ALL SELECT 'safety_status', safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
ORDER BY 1;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Revert Phase 7.8 consent/privacy process review. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--reviewed-by", default=None)
    parser.add_argument("--decision-notes", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF consent/privacy review revert. launch_key={args.launch_key}. Counts only; no contact values.")

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 4:
        print("Refusing: probe returned no usable result.")
        return 1
    log_rows, checks, perm_items = int(f[0] or 0), int(f[1] or 0), int(f[2] or 0)
    safety = f[3].strip()

    if log_rows == 0 and checks == 0 and perm_items == 0:
        print("Nothing to revert: no Phase 7.8 consent/privacy markers found for this launch_key.")
        return 0

    print("intended transitions:")
    print(f"  review-log rows (phase 7.8) -> deleted: {log_rows}")
    print(f"  readiness checks (lead_privacy_reviewed / consent_ready) -> restored: {checks}")
    print(f"  permission review items -> restored to prior status: {perm_items}")
    print(f"  current safety_status = {safety}")
    print("  guard: refuses if send/publish was enabled after review")
    print("  contacts / channel_permissions / leads / messages: UNTOUCHED")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key))
    print("Revert applied:" if code == 0 else "Revert FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
