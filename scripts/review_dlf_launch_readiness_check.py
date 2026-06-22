#!/usr/bin/env python3
"""Phase 7.6 — review/update ONE launch readiness check type. Dry-run by default.

Sets launch_readiness_checks.check_status for a given --check-type on the DLF launch
project, and stamps the reviewer/notes into raw_context. This is the SAFE, non-activation
readiness review tool. It only writes the launch_readiness_checks table; it never updates
send_enabled/publish_enabled, never activates n8n, and never creates/touches contacts,
leads, messages, or publishing.

Guardrails on PASSING (status in passed/waived):
  * project_name_confirmed   -> always refused here (use confirm_dlf_project_identity.py)
  * n8n activation checks     -> always refused here (no n8n activation this phase)
  * external/live checks (Wix landing page, lead capture form, form fields) -> refused
    unless --allow-non-activation-review is passed explicitly.
Setting failed/needs_review/pending is always allowed for any check type.

Writing requires BOTH --real-ok and --apply. Counts only; no raw personal values.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

VALID_STATUSES = {"passed", "failed", "waived", "needs_review", "pending"}
ADVANCING_STATUSES = {"passed", "waived"}  # statuses that move a gate toward "clear"

# Passing these here is always refused (they have a dedicated tool or imply going live).
HARD_REFUSE_PASS = {
    "project_name_confirmed",   # use confirm_dlf_project_identity.py
    "n8n_webhook_planned",      # no n8n activation this phase
    "n8n_workflow_ready",       # no n8n activation this phase
}
# Passing these requires explicit --allow-non-activation-review (they need an external
# system stood up, but passing the readiness row itself does not enable anything).
EXTERNAL_LIVE_PASS = {
    "wix_landing_page_ready",
    "lead_capture_form_ready",
    "wix_form_fields_reviewed",
}
def probe_sql(launch_key: str, check_type: str) -> str:
    lk = sql_literal(launch_key)
    ct = sql_literal(check_type)
    return f"""
SELECT
  (SELECT count(*) FROM launch_projects WHERE launch_key = {lk}),
  (SELECT count(*) FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id
     WHERE p.launch_key = {lk} AND r.check_type = {ct});
"""

def apply_sql(launch_key: str, check_type: str, status: str, by: str | None, notes: str | None) -> str:
    lk = sql_literal(launch_key)
    ct = sql_literal(check_type)
    st = sql_literal(status)
    rb = sql_literal(by)
    dn = sql_literal(notes)
    return f"""
BEGIN;
UPDATE launch_readiness_checks r
SET check_status = {st},
    raw_context = COALESCE(r.raw_context, '{{}}'::jsonb) || jsonb_build_object(
      'reviewed_by', {rb},
      'reviewed_at', to_jsonb(now()),
      'review_decision_notes', {dn},
      'review_phase', '7.6'
    ),
    updated_at = now()
FROM launch_projects p
WHERE p.id = r.launch_project_id AND p.launch_key = {lk} AND r.check_type = {ct};

-- Hard guardrail: a readiness review may NEVER flip a send/publish flag or n8n activation.
DO $$
DECLARE se int; pe int; an int;
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
  SELECT count(*) FROM launch_n8n_workflow_blueprints b JOIN launch_projects p ON p.id = b.launch_project_id
    WHERE p.launch_key = {lk} AND (b.workflow_status = 'active' OR b.activation_status = 'active') INTO an;
  IF se > 0 OR pe > 0 OR an > 0 THEN
    RAISE EXCEPTION 'Refusing: activation flag detected (send=%, publish=%, active_n8n=%).', se, pe, an;
  END IF;
END $$;
COMMIT;

SELECT 'check_type', {ct}
UNION ALL SELECT 'new_status', {st}
UNION ALL SELECT 'rows_updated', count(*)::text FROM launch_readiness_checks r
  JOIN launch_projects p ON p.id = r.launch_project_id
  WHERE p.launch_key = {lk} AND r.check_type = {ct} AND r.check_status = {st}
UNION ALL SELECT 'safety_status', safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_launch_push', ready_for_launch_push::text FROM vw_dlf_launch_priority_dashboard WHERE launch_key = {lk}
ORDER BY 1;
"""

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Review/update a launch readiness check (non-activation). Dry-run by default."
    )
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--check-type", required=True)
    parser.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    parser.add_argument("--reviewed-by", default=None)
    parser.add_argument("--decision-notes", default=None)
    parser.add_argument("--allow-non-activation-review", action="store_true",
                        help="required to pass external/live checks (Wix/lead-capture readiness)")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF readiness review. launch_key={args.launch_key} check_type={args.check_type} status={args.status}. Counts only.")

    advancing = args.status in ADVANCING_STATUSES

    if advancing and args.check_type in HARD_REFUSE_PASS:
        print(f"Refusing: '{args.check_type}' cannot be passed/waived by this generic tool "
              "(project name uses confirm_dlf_project_identity.py; n8n activation is out of scope this phase).")
        return 1
    if advancing and args.check_type in EXTERNAL_LIVE_PASS and not args.allow_non_activation_review:
        print(f"Refusing: '{args.check_type}' requires an external system to be live; "
              "pass --allow-non-activation-review to record this review explicitly.")
        return 1

    code, probe = run_psql(probe_sql(args.launch_key, args.check_type))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 2:
        print("Refusing: probe returned no usable result.")
        return 1
    project_exists = int(f[0] or 0)
    check_rows = int(f[1] or 0)
    if project_exists != 1:
        print("Refusing: launch project not found for this launch_key.")
        return 1
    if check_rows < 1:
        print(f"Refusing: check type '{args.check_type}' not found for this launch project.")
        return 1

    print("intended transition:")
    print(f"  launch_readiness_checks[{args.check_type}].check_status -> {args.status} ({check_rows} row[s])")
    print("  launch_readiness_checks.raw_context: reviewed_by, reviewed_at, notes, review_phase=7.6")
    print("  send_enabled / publish_enabled / n8n activation / contacts / leads / messages: UNTOUCHED")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key, args.check_type, args.status, args.reviewed_by, args.decision_notes))
    print("Readiness review applied:" if code == 0 else "Readiness review FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
