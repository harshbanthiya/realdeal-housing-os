#!/usr/bin/env python3
"""Phase 7.18 — revert the DLF Westpark "Gallery White" design-direction review. Dry-run by default.

Restores ONLY the rows changed by review_dlf_gallery_white_design_direction.py, identified by
the `phase_7_18_action` marker stamped into raw_context:

  * fable_design_outputs        -> output_status restored from phase_7_18_prev_output_status
  * design_second_opinion_reviews -> review_status restored from phase_7_18_prev_review_status
  * design_refinement_actions   -> action_status restored from phase_7_18_prev_action_status
  * fable_design_review_items    -> status restored from phase_7_18_prev_status; reviewer fields cleared

All Phase 7.18 markers (and build_ready_acknowledged) are removed. It never deletes the captured
Phase 7.17 rows, never deletes raw artifacts, and never touches contacts/leads/messages. An
in-transaction guard refuses if any reviewed row is marked external_call_made, if send/publish is
enabled, or if any Wix page was created/published.

Reverting requires BOTH --real-ok and --apply. Counts only.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.18"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def sql_literal(value) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    command = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql", "-U", user, "-d", db_name,
        "-v", "ON_ERROR_STOP=1", "-At", "-F", "|",
    ]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk})
SELECT
  (SELECT count(*) FROM fable_design_outputs o WHERE o.launch_project_id IN (SELECT id FROM proj) AND o.raw_context->>'phase_7_18_action' = 'output_accepted'),
  (SELECT count(*) FROM design_second_opinion_reviews r WHERE r.launch_project_id IN (SELECT id FROM proj) AND r.raw_context->>'phase_7_18_action' = 'gemini_accepted'),
  (SELECT count(*) FROM design_refinement_actions a WHERE a.launch_project_id IN (SELECT id FROM proj) AND a.raw_context->>'phase_7_18_action' = 'action_accepted'),
  (SELECT count(*) FROM fable_design_review_items ri WHERE ri.launch_project_id IN (SELECT id FROM proj) AND ri.raw_context->>'phase_7_18_action' = 'item_approved'),
  (SELECT count(*) FROM fable_design_outputs o WHERE o.launch_project_id IN (SELECT id FROM proj) AND o.external_call_made)
    + (SELECT count(*) FROM design_second_opinion_reviews r WHERE r.launch_project_id IN (SELECT id FROM proj) AND r.external_call_made),
  COALESCE((SELECT send_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}), 0),
  COALESCE((SELECT publish_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}), 0),
  (SELECT count(*) FROM wix_page_blueprints w WHERE w.launch_project_id IN (SELECT id FROM proj) AND (w.publish_enabled OR w.page_status = 'published'));
"""


def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;
DO $GUARD$
DECLARE ext int; se int; pe int; wix int;
BEGIN
  SELECT
      (SELECT count(*) FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id WHERE p.launch_key = {lk} AND o.external_call_made)
    + (SELECT count(*) FROM design_second_opinion_reviews r JOIN launch_projects p ON p.id = r.launch_project_id WHERE p.launch_key = {lk} AND r.external_call_made)
  INTO ext;
  SELECT send_enabled_count INTO se FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT publish_enabled_count INTO pe FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT count(*) INTO wix FROM wix_page_blueprints w JOIN launch_projects p ON p.id = w.launch_project_id
    WHERE p.launch_key = {lk} AND (w.publish_enabled OR w.page_status = 'published');
  IF ext > 0 THEN RAISE EXCEPTION 'Refusing revert: external_call_made row exists (%).', ext; END IF;
  IF se > 0 OR pe > 0 THEN RAISE EXCEPTION 'Refusing revert: send/publish enabled (send=%, publish=%).', se, pe; END IF;
  IF wix > 0 THEN RAISE EXCEPTION 'Refusing revert: a Wix page was created/published (%).', wix; END IF;
END $GUARD$;

UPDATE fable_design_outputs o SET
  output_status = COALESCE(o.raw_context->>'phase_7_18_prev_output_status', o.output_status),
  raw_context = (o.raw_context - 'phase_7_18_action' - 'phase_7_18_prev_output_status' - 'phase_7_18_reviewed_by' - 'build_ready_acknowledged'),
  updated_at = now()
FROM launch_projects p
WHERE p.id = o.launch_project_id AND p.launch_key = {lk}
  AND o.raw_context->>'phase_7_18_action' = 'output_accepted';

UPDATE design_second_opinion_reviews r SET
  review_status = COALESCE(r.raw_context->>'phase_7_18_prev_review_status', r.review_status),
  raw_context = (r.raw_context - 'phase_7_18_action' - 'phase_7_18_prev_review_status' - 'phase_7_18_reviewed_by'),
  updated_at = now()
FROM launch_projects p
WHERE p.id = r.launch_project_id AND p.launch_key = {lk}
  AND r.raw_context->>'phase_7_18_action' = 'gemini_accepted';

UPDATE design_refinement_actions a SET
  action_status = COALESCE(a.raw_context->>'phase_7_18_prev_action_status', a.action_status),
  raw_context = (a.raw_context - 'phase_7_18_action' - 'phase_7_18_prev_action_status' - 'phase_7_18_reviewed_by'),
  updated_at = now()
FROM launch_projects p
WHERE p.id = a.launch_project_id AND p.launch_key = {lk}
  AND a.raw_context->>'phase_7_18_action' = 'action_accepted';

UPDATE fable_design_review_items ri SET
  status = COALESCE(ri.raw_context->>'phase_7_18_prev_status', ri.status),
  reviewed_by = NULL, reviewed_at = NULL, decision_notes = NULL,
  raw_context = (ri.raw_context - 'phase_7_18_action' - 'phase_7_18_prev_status'),
  updated_at = now()
FROM launch_projects p
WHERE p.id = ri.launch_project_id AND p.launch_key = {lk}
  AND ri.raw_context->>'phase_7_18_action' = 'item_approved';
COMMIT;

SELECT 'output_accepted_direction', count(*)::text FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id WHERE p.launch_key = {lk} AND o.output_status = 'accepted_direction' AND o.raw_context->>'phase' = '7.17'
UNION ALL SELECT 'gemini_accepted_guidance', count(*)::text FROM design_second_opinion_reviews r JOIN launch_projects p ON p.id = r.launch_project_id WHERE p.launch_key = {lk} AND r.review_status = 'accepted_guidance' AND r.raw_context->>'phase' = '7.17'
UNION ALL SELECT 'refinement_actions_accepted', count(*)::text FROM design_refinement_actions a JOIN launch_projects p ON p.id = a.launch_project_id WHERE p.launch_key = {lk} AND a.action_status = 'accepted' AND a.raw_context->>'phase' = '7.17'
UNION ALL SELECT 'review_items_approved', count(*)::text FROM fable_design_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.status = 'approved' AND ri.raw_context->>'phase' = '7.17'
UNION ALL SELECT 'review_items_pending', count(*)::text FROM fable_design_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.status = 'pending' AND ri.raw_context->>'phase' = '7.17'
UNION ALL SELECT 'ready_for_wix_design_build', ready_for_wix_design_build::text FROM vw_dlf_design_output_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'external_call_made_count', external_call_made_count::text FROM vw_dlf_design_output_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'inbound_leads', count(*)::text FROM inbound_leads
UNION ALL SELECT 'contacts', count(*)::text FROM contacts
ORDER BY 1;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Revert Phase 7.18 Gallery White design review. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Gallery White design-review revert. launch_key={args.launch_key}. Counts only.")
    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 8:
        print("Refusing: probe returned no usable result.")
        return 1
    outputs, reviews, actions, items, ext, se, pe, wix = (int(x or 0) for x in f[:8])
    if ext or se or pe or wix:
        print("Refusing revert: external/send/publish/wix-page flags are present.")
        print(f"  external_call_made: {ext}   send_enabled: {se}   publish_enabled: {pe}   wix_pages_published: {wix}")
        return 1

    print("intended reverts (Phase 7.18 marked rows only):")
    print(f"  fable_design_outputs: {outputs}   second_opinion_reviews: {reviews}   "
          f"refinement_actions: {actions}   review_items: {items}")
    print("  Phase 7.17 captured rows and raw artifacts: PRESERVED")
    print("  contacts/leads/messages: untouched")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Reverting requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key))
    print("Revert applied:" if code == 0 else "Revert FAILED (rolled back):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
