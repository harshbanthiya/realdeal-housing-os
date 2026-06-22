#!/usr/bin/env python3
"""Phase 7.6 — revert a Phase 7.6 project-identity confirmation. Dry-run by default.

Undoes ONLY a confirmation written by confirm_dlf_project_identity.py (identified by
raw_context.confirmation_source = 'phase_7_6_project_identity_confirmation'). It:
  - restores launch_projects.project_display_name from raw_context.previous_display_name
  - clears the confirmation keys and sets raw_context.project_name_confirmed = false
  - sets the launch_readiness_checks[project_name_confirmed] row back to pending
  - sets launch_operator_tasks[verify_project_name] back to pending

It REFUSES if any send/publish flag was enabled after the confirmation (you must stand the
launch back down first). It never touches contacts, leads, messages, or n8n activation.

Writing requires BOTH --real-ok and --apply. Counts only; no raw personal values.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIRMATION_SOURCE = "phase_7_6_project_identity_confirmation"
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT
  (SELECT count(*) FROM launch_projects WHERE launch_key = {lk}
     AND raw_context->>'project_name_confirmed' = 'true'
     AND raw_context->>'confirmation_source' = '{CONFIRMATION_SOURCE}'),
  COALESCE((SELECT raw_context ? 'previous_display_name' FROM launch_projects WHERE launch_key = {lk}), false)::text,
  (SELECT safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk});
"""

def apply_sql(launch_key: str, reverted_by: str | None, revert_notes: str | None) -> str:
    lk = sql_literal(launch_key)
    rb = sql_literal(reverted_by)
    rn = sql_literal(revert_notes)
    return f"""
BEGIN;
CREATE TEMP TABLE tmp_rev AS
SELECT id, raw_context->>'previous_display_name' AS prev_name
FROM launch_projects
WHERE launch_key = {lk}
  AND raw_context->>'project_name_confirmed' = 'true'
  AND raw_context->>'confirmation_source' = '{CONFIRMATION_SOURCE}';

DO $$
BEGIN
  IF (SELECT count(*) FROM tmp_rev) <> 1 THEN
    RAISE EXCEPTION 'Expected exactly 1 Phase 7.6 confirmation to revert, got %.', (SELECT count(*) FROM tmp_rev);
  END IF;
END $$;

-- Refuse if anything was activated after the confirmation.
DO $$
DECLARE se int; pe int;
BEGIN
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN tmp_rev t ON t.id = lc.launch_project_id WHERE lc.send_enabled)
    + (SELECT count(*) FROM launch_message_templates m JOIN tmp_rev t ON t.id = m.launch_project_id WHERE m.send_enabled)
    + (SELECT count(*) FROM launch_campaign_calendar cc JOIN tmp_rev t ON t.id = cc.launch_project_id WHERE cc.send_enabled)
  INTO se;
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN tmp_rev t ON t.id = lc.launch_project_id WHERE lc.publish_enabled)
    + (SELECT count(*) FROM launch_landing_page_specs s JOIN tmp_rev t ON t.id = s.launch_project_id WHERE s.publish_enabled)
    + (SELECT count(*) FROM launch_lead_capture_forms f JOIN tmp_rev t ON t.id = f.launch_project_id WHERE f.publish_enabled)
    + (SELECT count(*) FROM launch_social_content_drafts sc JOIN tmp_rev t ON t.id = sc.launch_project_id WHERE sc.publish_enabled)
    + (SELECT count(*) FROM launch_campaign_calendar cc JOIN tmp_rev t ON t.id = cc.launch_project_id WHERE cc.publish_enabled)
  INTO pe;
  IF se > 0 OR pe > 0 THEN
    RAISE EXCEPTION 'Refusing revert: send/publish was enabled after confirmation (send=%, publish=%). Stand the launch down first.', se, pe;
  END IF;
END $$;

UPDATE launch_projects p
SET project_display_name = COALESCE(t.prev_name, p.project_display_name),
    raw_context = (p.raw_context
      - 'confirmed_project_display_name' - 'confirmed_public_slug' - 'confirmed_by'
      - 'confirmed_at' - 'previous_display_name' - 'confirmation_phase'
      - 'confirmation_source' - 'confirmation_decision_notes')
      || jsonb_build_object(
           'project_name_confirmed', false,
           'name_confirmation_reverted_phase', '7.6',
           'name_confirmation_reverted_by', {rb},
           'name_confirmation_revert_notes', {rn},
           'name_confirmation_reverted_at', to_jsonb(now())
         ),
    updated_at = now()
FROM tmp_rev t
WHERE p.id = t.id;

UPDATE launch_readiness_checks r
SET check_status = 'pending',
    safe_summary = 'Project name confirmation reverted; operator must re-confirm.',
    updated_at = now()
FROM tmp_rev t
WHERE r.launch_project_id = t.id AND r.check_type = 'project_name_confirmed';

UPDATE launch_operator_tasks tk
SET task_status = 'pending', updated_at = now()
FROM tmp_rev t
WHERE tk.launch_project_id = t.id AND tk.task_type = 'verify_project_name';
COMMIT;

SELECT 'project_name_confirmed_flag', COALESCE((SELECT raw_context->>'project_name_confirmed' FROM launch_projects WHERE launch_key = {lk}), 'false')
UNION ALL SELECT 'readiness_project_name_pending', count(*)::text FROM launch_readiness_checks r
  JOIN launch_projects p ON p.id = r.launch_project_id
  WHERE p.launch_key = {lk} AND r.check_type = 'project_name_confirmed' AND r.check_status = 'pending'
UNION ALL SELECT 'verify_project_name_pending', count(*)::text FROM launch_operator_tasks tk
  JOIN launch_projects p ON p.id = tk.launch_project_id
  WHERE p.launch_key = {lk} AND tk.task_type = 'verify_project_name' AND tk.task_status = 'pending'
UNION ALL SELECT 'safety_status', safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
ORDER BY 1;
"""

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Revert a Phase 7.6 project-identity confirmation. Dry-run by default."
    )
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--reviewed-by", default=None)
    parser.add_argument("--decision-notes", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF project identity revert. launch_key={args.launch_key}. Counts only; no personal data.")

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 3:
        print("Refusing: probe returned no usable result.")
        return 1
    confirmations = int(f[0] or 0)
    # boolean::text yields 'true'/'false' (not 't'/'f').
    has_prev = f[1].strip() == "true"
    safety = f[2].strip()

    if confirmations != 1:
        print("Nothing to revert: no Phase 7.6 project-identity confirmation found for this launch_key.")
        return 0

    print("intended transitions:")
    print(f"  launch_projects.project_display_name -> previous_display_name ({'present' if has_prev else 'missing -> kept'})")
    print("  launch_projects.raw_context: project_name_confirmed -> false; confirmation keys cleared")
    print("  launch_readiness_checks[project_name_confirmed] -> pending")
    print("  launch_operator_tasks[verify_project_name] -> pending")
    print(f"  current safety_status = {safety}")
    print("  guard: refuses if send/publish was enabled after confirmation")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key, args.reviewed_by, args.decision_notes))
    print("Revert applied:" if code == 0 else "Revert FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
