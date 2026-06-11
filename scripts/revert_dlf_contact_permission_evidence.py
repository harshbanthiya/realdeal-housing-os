#!/usr/bin/env python3
"""Phase 7.9 — revert the DLF contact permission evidence & suppression review. Dry-run by default.

Undoes ONLY what review_dlf_contact_permission_evidence.py wrote (raw_context.phase = '7.9'):
  - deletes Phase 7.9 launch_contact_permission_evidence rows;
  - deletes Phase 7.9 launch_contact_suppression_checks rows;
  - restores candidate suppression_status from raw_context.phase_7_9_suppression_prev and clears the marker;
  - restores Phase 7.9-approved suppression_review items to their prior status (clearing reviewer/notes);
  - deletes Phase 7.9 launch_contact_permission_decision_log rows.

It REFUSES if any candidate became approved_for_segment or any send/publish flag became true. It never
touches contacts, channel_permissions, outreach_suppression_list, leads, or messages.

Writing requires BOTH --real-ok and --apply. Counts only; never prints contact values.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def sql_literal(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


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
SELECT
  (SELECT count(*) FROM launch_contact_permission_evidence e JOIN launch_projects p ON p.id = e.launch_project_id WHERE p.launch_key = {lk} AND e.raw_context->>'phase' = '7.9'),
  (SELECT count(*) FROM launch_contact_suppression_checks s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk} AND s.raw_context->>'phase' = '7.9'),
  (SELECT count(*) FROM launch_contact_permission_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '7.9'),
  (SELECT count(*) FROM launch_contact_segment_candidates c JOIN launch_projects p ON p.id = c.launch_project_id WHERE p.launch_key = {lk} AND c.raw_context ? 'phase_7_9_suppression_prev'),
  (SELECT count(*) FROM launch_contact_permission_decision_log l JOIN launch_projects p ON p.id = l.launch_project_id WHERE p.launch_key = {lk} AND l.raw_context->>'phase' = '7.9'),
  (SELECT safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk});
"""


def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
BEGIN;
-- Refuse if anything was activated/approved after the review.
DO $GUARD$
DECLARE se int; pe int; aff int;
BEGIN
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN launch_projects p ON p.id = lc.launch_project_id WHERE p.launch_key = {lk} AND lc.send_enabled)
    + (SELECT count(*) FROM launch_message_templates m JOIN launch_projects p ON p.id = m.launch_project_id WHERE p.launch_key = {lk} AND m.send_enabled)
  INTO se;
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN launch_projects p ON p.id = lc.launch_project_id WHERE p.launch_key = {lk} AND lc.publish_enabled)
    + (SELECT count(*) FROM launch_landing_page_specs s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk} AND s.publish_enabled)
    + (SELECT count(*) FROM launch_lead_capture_forms f JOIN launch_projects p ON p.id = f.launch_project_id WHERE p.launch_key = {lk} AND f.publish_enabled)
    + (SELECT count(*) FROM launch_social_content_drafts sc JOIN launch_projects p ON p.id = sc.launch_project_id WHERE p.launch_key = {lk} AND sc.publish_enabled)
  INTO pe;
  SELECT count(*) FROM launch_contact_segment_candidates c JOIN launch_projects p ON p.id = c.launch_project_id
    WHERE p.launch_key = {lk} AND c.candidate_status = 'approved_for_segment' INTO aff;
  IF se > 0 OR pe > 0 THEN RAISE EXCEPTION 'Refusing revert: send/publish enabled after review (send=%, publish=%).', se, pe; END IF;
  IF aff > 0 THEN RAISE EXCEPTION 'Refusing revert: % candidate(s) approved_for_segment after review.', aff; END IF;
END $GUARD$;

-- 1. Restore suppression_review items approved by Phase 7.9.
UPDATE launch_contact_permission_review_items ri SET
  status = COALESCE(ri.raw_context->>'phase_7_9_prev_status', 'pending'),
  reviewed_by = NULL, reviewed_at = NULL, decision_notes = NULL,
  raw_context = ri.raw_context - 'phase' - 'phase_7_9_action' - 'phase_7_9_prev_status',
  updated_at = now()
FROM launch_projects p
WHERE p.id = ri.launch_project_id AND p.launch_key = {lk} AND ri.raw_context->>'phase' = '7.9';

-- 2. Restore candidate suppression_status.
UPDATE launch_contact_segment_candidates cand SET
  suppression_status = COALESCE(cand.raw_context->>'phase_7_9_suppression_prev', cand.suppression_status),
  raw_context = cand.raw_context - 'phase_7_9_suppression_prev',
  updated_at = now()
FROM launch_projects p
WHERE p.id = cand.launch_project_id AND p.launch_key = {lk} AND cand.raw_context ? 'phase_7_9_suppression_prev';

-- 3. Delete Phase 7.9 evidence / suppression checks / decision log.
DELETE FROM launch_contact_permission_evidence e USING launch_projects p
  WHERE p.id = e.launch_project_id AND p.launch_key = {lk} AND e.raw_context->>'phase' = '7.9';
DELETE FROM launch_contact_suppression_checks s USING launch_projects p
  WHERE p.id = s.launch_project_id AND p.launch_key = {lk} AND s.raw_context->>'phase' = '7.9';
DELETE FROM launch_contact_permission_decision_log l USING launch_projects p
  WHERE p.id = l.launch_project_id AND p.launch_key = {lk} AND l.raw_context->>'phase' = '7.9';
COMMIT;

SELECT 'evidence_phase_7_9_remaining', count(*)::text FROM launch_contact_permission_evidence e JOIN launch_projects p ON p.id = e.launch_project_id WHERE p.launch_key = {lk} AND e.raw_context->>'phase' = '7.9'
UNION ALL SELECT 'suppression_checks_phase_7_9_remaining', count(*)::text FROM launch_contact_suppression_checks s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk} AND s.raw_context->>'phase' = '7.9'
UNION ALL SELECT 'decision_log_phase_7_9_remaining', count(*)::text FROM launch_contact_permission_decision_log l JOIN launch_projects p ON p.id = l.launch_project_id WHERE p.launch_key = {lk} AND l.raw_context->>'phase' = '7.9'
UNION ALL SELECT 'suppression_reviews_pending', count(*)::text FROM launch_contact_permission_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.review_type = 'suppression_review' AND ri.status = 'pending'
UNION ALL SELECT 'safety_status', safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
ORDER BY 1;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Revert Phase 7.9 contact permission evidence review. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--reviewed-by", default=None)
    parser.add_argument("--decision-notes", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF permission evidence revert. launch_key={args.launch_key}. Counts only; no contact values.")

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 6:
        print("Refusing: probe returned no usable result.")
        return 1
    evidence, checks, perm_items, cand_supp, log_rows = (int(x or 0) for x in f[:5])
    safety = f[5].strip()

    if evidence == 0 and checks == 0 and perm_items == 0 and cand_supp == 0 and log_rows == 0:
        print("Nothing to revert: no Phase 7.9 permission-evidence markers found for this launch_key.")
        return 0

    print("intended transitions:")
    print(f"  permission evidence rows -> deleted: {evidence}")
    print(f"  suppression check rows -> deleted: {checks}")
    print(f"  decision-log rows -> deleted: {log_rows}")
    print(f"  suppression_review items -> restored to prior status: {perm_items}")
    print(f"  candidate suppression_status -> restored: {cand_supp}")
    print(f"  current safety_status = {safety}")
    print("  guard: refuses if send/publish enabled or any candidate approved_for_segment")
    print("  contacts / channel_permissions / outreach_suppression_list / leads / messages: UNTOUCHED")

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
