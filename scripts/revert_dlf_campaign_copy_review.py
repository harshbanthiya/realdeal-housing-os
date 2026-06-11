#!/usr/bin/env python3
"""Phase 7.7 — revert the internal DLF campaign copy review. Dry-run by default.

Undoes ONLY what review_dlf_campaign_copy.py wrote, identified by its raw_context markers:
  - review items with raw_context.phase = '7.7' -> status restored to phase_7_7_prev_status
    ('pending'); reviewed_by/reviewed_at/decision_notes cleared; phase_7_7 keys removed.
  - message templates / social drafts / landing page with raw_context.phase_7_7_project_name_replaced
    = true -> "DLF Westpark" swapped back to [PROJECT_NAME_CONFIRM] in their text fields; marker keys
    removed.
  - internal_copy_reviewed markers removed from any content that carries the phase_7_7 stamp.

It REFUSES if any send/publish flag became true after the review. It never touches contacts,
permission reviews, leads, messages, readiness checks, or send/publish flags.

Writing requires BOTH --real-ok and --apply. Counts only; no copy bodies / no personal data.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"

PROJECT_NAME_TOKEN = "[PROJECT_NAME_CONFIRM]"
CONFIRMED_NAME = "DLF Westpark"
COPY_REVIEW_TYPES = (
    "whatsapp_copy_review", "email_copy_review", "social_copy_review",
    "compliance_review", "consent_review",
)


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


def review_types_sql() -> str:
    return ", ".join(sql_literal(t) for t in COPY_REVIEW_TYPES)


def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT
  (SELECT count(*) FROM launch_draft_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id
     WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '7.7'),
  (SELECT count(*) FROM launch_message_templates t JOIN launch_projects p ON p.id = t.launch_project_id
     WHERE p.launch_key = {lk} AND t.raw_context->>'phase_7_7_project_name_replaced' = 'true'),
  (SELECT count(*) FROM launch_social_content_drafts s JOIN launch_projects p ON p.id = s.launch_project_id
     WHERE p.launch_key = {lk} AND s.raw_context->>'phase_7_7_project_name_replaced' = 'true'),
  (SELECT count(*) FROM launch_landing_page_specs l JOIN launch_projects p ON p.id = l.launch_project_id
     WHERE p.launch_key = {lk} AND l.raw_context->>'phase_7_7_project_name_replaced' = 'true'),
  (SELECT safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk});
"""


def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    name = sql_literal(CONFIRMED_NAME)
    token = sql_literal(PROJECT_NAME_TOKEN)
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

-- 1. Restore review items.
UPDATE launch_draft_review_items ri SET
  status = coalesce(ri.raw_context->>'phase_7_7_prev_status', 'pending'),
  reviewed_by = NULL, reviewed_at = NULL, decision_notes = NULL,
  raw_context = ri.raw_context - 'phase' - 'phase_7_7_action' - 'phase_7_7_prev_status',
  updated_at = now()
FROM launch_projects p
WHERE p.id = ri.launch_project_id AND p.launch_key = {lk} AND ri.raw_context->>'phase' = '7.7';

-- 2. Restore project-name placeholder in templates / social / landing.
UPDATE launch_message_templates t SET
  subject = replace(t.subject, {name}, {token}),
  body = replace(t.body, {name}, {token}),
  cta = replace(t.cta, {name}, {token}),
  raw_context = t.raw_context - 'phase_7_7_project_name_replaced' - 'phase_7_7_project_name_value'
                - 'internal_copy_reviewed' - 'phase_7_7_internal_copy_reviewed',
  updated_at = now()
FROM launch_projects p
WHERE p.id = t.launch_project_id AND p.launch_key = {lk}
  AND t.raw_context->>'phase_7_7_project_name_replaced' = 'true';

UPDATE launch_social_content_drafts s SET
  hook = replace(s.hook, {name}, {token}),
  caption = replace(s.caption, {name}, {token}),
  cta = replace(s.cta, {name}, {token}),
  hashtags = replace(s.hashtags, {name}, {token}),
  visual_direction = replace(s.visual_direction, {name}, {token}),
  raw_context = s.raw_context - 'phase_7_7_project_name_replaced' - 'phase_7_7_project_name_value'
                - 'internal_copy_reviewed' - 'phase_7_7_internal_copy_reviewed',
  updated_at = now()
FROM launch_projects p
WHERE p.id = s.launch_project_id AND p.launch_key = {lk}
  AND s.raw_context->>'phase_7_7_project_name_replaced' = 'true';

UPDATE launch_landing_page_specs l SET
  page_title = replace(l.page_title, {name}, {token}),
  hero_headline = replace(l.hero_headline, {name}, {token}),
  hero_subheadline = replace(l.hero_subheadline, {name}, {token}),
  primary_cta = replace(l.primary_cta, {name}, {token}),
  secondary_cta = replace(l.secondary_cta, {name}, {token}),
  raw_context = l.raw_context - 'phase_7_7_project_name_replaced' - 'phase_7_7_project_name_value',
  updated_at = now()
FROM launch_projects p
WHERE p.id = l.launch_project_id AND p.launch_key = {lk}
  AND l.raw_context->>'phase_7_7_project_name_replaced' = 'true';

-- 3. Remove any lingering internal_copy_reviewed stamps tied to phase 7.7 (approved-only items).
UPDATE launch_message_templates t SET
  raw_context = t.raw_context - 'internal_copy_reviewed' - 'phase_7_7_internal_copy_reviewed', updated_at = now()
FROM launch_projects p
WHERE p.id = t.launch_project_id AND p.launch_key = {lk}
  AND t.raw_context->>'phase_7_7_internal_copy_reviewed' = 'true';

UPDATE launch_social_content_drafts s SET
  raw_context = s.raw_context - 'internal_copy_reviewed' - 'phase_7_7_internal_copy_reviewed', updated_at = now()
FROM launch_projects p
WHERE p.id = s.launch_project_id AND p.launch_key = {lk}
  AND s.raw_context->>'phase_7_7_internal_copy_reviewed' = 'true';
COMMIT;

SELECT 'review_items_phase_7_7_remaining', count(*)::text FROM launch_draft_review_items ri
  JOIN launch_projects p ON p.id = ri.launch_project_id
  WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '7.7'
UNION ALL SELECT 'project_name_token_templates', count(*)::text FROM launch_message_templates
  WHERE launch_project_id IN (SELECT id FROM launch_projects WHERE launch_key = {lk})
    AND (subject LIKE '%'||{token}||'%' OR body LIKE '%'||{token}||'%' OR cta LIKE '%'||{token}||'%')
UNION ALL SELECT 'safety_status', safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
ORDER BY 1;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Revert Phase 7.7 campaign copy review. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--reviewed-by", default=None)
    parser.add_argument("--decision-notes", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF campaign copy review revert. launch_key={args.launch_key}. Counts only; no copy bodies / no personal data.")

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 5:
        print("Refusing: probe returned no usable result.")
        return 1
    review_items, tmpl_repl, social_repl, landing_repl = int(f[0] or 0), int(f[1] or 0), int(f[2] or 0), int(f[3] or 0)
    safety = f[4].strip()

    if review_items == 0 and tmpl_repl == 0 and social_repl == 0 and landing_repl == 0:
        print("Nothing to revert: no Phase 7.7 copy-review markers found for this launch_key.")
        return 0

    print("intended transitions:")
    print(f"  review items (phase 7.7) -> restored to prev status: {review_items}")
    print(f"  templates with name replaced -> placeholder restored: {tmpl_repl}")
    print(f"  social drafts with name replaced -> placeholder restored: {social_repl}")
    print(f"  landing page with name replaced -> placeholder restored: {landing_repl}")
    print(f"  current safety_status = {safety}")
    print("  guard: refuses if send/publish was enabled after review")
    print("  contacts / permission reviews / leads / readiness checks: UNTOUCHED")

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
