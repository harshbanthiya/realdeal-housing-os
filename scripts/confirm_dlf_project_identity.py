#!/usr/bin/env python3
"""Phase 7.6 — confirm the DLF launch project's public name. Dry-run by default.

Applies an OPERATOR-SUPPLIED confirmed public project name to the launch project. It
NEVER invents, guesses, or web-verifies the name; the confirmed name MUST be passed in
explicitly. On apply it:
  - sets launch_projects.project_display_name to the confirmed value
  - stamps launch_projects.raw_context: project_name_confirmed=true,
    confirmed_project_display_name, confirmed_public_slug (optional), confirmed_by,
    confirmed_at, previous_display_name
  - passes the launch_readiness_checks row check_type='project_name_confirmed'
  - marks launch_operator_tasks task_type='verify_project_name' as done

It does NOT touch send_enabled/publish_enabled, does NOT approve copy/templates, does NOT
update contacts, does NOT call any external API, and a hard in-transaction guard rolls the
whole thing back if any send/publish flag or ready_for_launch_push would become true.

Writing requires BOTH --real-ok and --apply. Counts only; no raw personal values.
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
  (SELECT count(*) FROM launch_projects WHERE launch_key = {lk}),
  COALESCE((SELECT raw_context->>'project_name_confirmed' FROM launch_projects WHERE launch_key = {lk}), 'false'),
  (SELECT count(*) FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id
     WHERE p.launch_key = {lk} AND r.check_type = 'project_name_confirmed' AND r.check_status <> 'passed'),
  (SELECT count(*) FROM launch_operator_tasks tk JOIN launch_projects p ON p.id = tk.launch_project_id
     WHERE p.launch_key = {lk} AND tk.task_type = 'verify_project_name' AND tk.task_status <> 'done');
"""


def apply_sql(launch_key: str, name: str, slug: str | None, by: str, notes: str | None) -> str:
    lk = sql_literal(launch_key)
    nm = sql_literal(name)
    sl = sql_literal(slug)
    rb = sql_literal(by)
    dn = sql_literal(notes)
    return f"""
BEGIN;
CREATE TEMP TABLE tmp_conf AS
SELECT id, project_display_name AS old_display_name
FROM launch_projects
WHERE launch_key = {lk}
  AND COALESCE(raw_context->>'project_name_confirmed', 'false') <> 'true';

DO $$
BEGIN
  IF (SELECT count(*) FROM tmp_conf) <> 1 THEN
    RAISE EXCEPTION 'Expected exactly 1 unconfirmed launch project for this key, got %.', (SELECT count(*) FROM tmp_conf);
  END IF;
END $$;

UPDATE launch_projects p
SET project_display_name = {nm},
    raw_context = p.raw_context || jsonb_build_object(
      'project_name_confirmed', true,
      'confirmed_project_display_name', {nm},
      'confirmed_public_slug', {sl},
      'confirmed_by', {rb},
      'confirmed_at', to_jsonb(now()),
      'previous_display_name', t.old_display_name,
      'confirmation_phase', '7.6',
      'confirmation_source', 'phase_7_6_project_identity_confirmation',
      'confirmation_decision_notes', {dn}
    ),
    updated_at = now()
FROM tmp_conf t
WHERE p.id = t.id;

UPDATE launch_readiness_checks r
SET check_status = 'passed',
    safe_summary = 'Operator confirmed public project name.',
    updated_at = now()
FROM tmp_conf t
WHERE r.launch_project_id = t.id AND r.check_type = 'project_name_confirmed';

UPDATE launch_operator_tasks tk
SET task_status = 'done', updated_at = now()
FROM tmp_conf t
WHERE tk.launch_project_id = t.id AND tk.task_type = 'verify_project_name';

-- Hard guardrail: this confirmation may NEVER enable sending/publishing/launch.
DO $$
DECLARE se int; pe int; rf boolean;
BEGIN
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN tmp_conf t ON t.id = lc.launch_project_id WHERE lc.send_enabled)
    + (SELECT count(*) FROM launch_message_templates m JOIN tmp_conf t ON t.id = m.launch_project_id WHERE m.send_enabled)
    + (SELECT count(*) FROM launch_campaign_calendar cc JOIN tmp_conf t ON t.id = cc.launch_project_id WHERE cc.send_enabled)
  INTO se;
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN tmp_conf t ON t.id = lc.launch_project_id WHERE lc.publish_enabled)
    + (SELECT count(*) FROM launch_landing_page_specs s JOIN tmp_conf t ON t.id = s.launch_project_id WHERE s.publish_enabled)
    + (SELECT count(*) FROM launch_lead_capture_forms f JOIN tmp_conf t ON t.id = f.launch_project_id WHERE f.publish_enabled)
    + (SELECT count(*) FROM launch_social_content_drafts sc JOIN tmp_conf t ON t.id = sc.launch_project_id WHERE sc.publish_enabled)
    + (SELECT count(*) FROM launch_campaign_calendar cc JOIN tmp_conf t ON t.id = cc.launch_project_id WHERE cc.publish_enabled)
  INTO pe;
  SELECT ready_for_launch_push INTO rf FROM vw_dlf_launch_priority_dashboard WHERE launch_key = {lk};
  IF se > 0 OR pe > 0 THEN
    RAISE EXCEPTION 'Refusing: send/publish flags would be enabled (send=%, publish=%).', se, pe;
  END IF;
  IF rf THEN
    RAISE EXCEPTION 'Refusing: ready_for_launch_push would be true after confirmation.';
  END IF;
END $$;
COMMIT;

SELECT 'project_name_confirmed_flag', COALESCE((SELECT raw_context->>'project_name_confirmed' FROM launch_projects WHERE launch_key = {lk}), 'false')
UNION ALL SELECT 'readiness_project_name_passed', count(*)::text FROM launch_readiness_checks r
  JOIN launch_projects p ON p.id = r.launch_project_id
  WHERE p.launch_key = {lk} AND r.check_type = 'project_name_confirmed' AND r.check_status = 'passed'
UNION ALL SELECT 'verify_project_name_done', count(*)::text FROM launch_operator_tasks tk
  JOIN launch_projects p ON p.id = tk.launch_project_id
  WHERE p.launch_key = {lk} AND tk.task_type = 'verify_project_name' AND tk.task_status = 'done'
UNION ALL SELECT 'ready_for_launch_push', ready_for_launch_push::text FROM vw_dlf_launch_priority_dashboard WHERE launch_key = {lk}
UNION ALL SELECT 'safety_status', safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
ORDER BY 1;
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Confirm DLF launch project public name from operator-supplied value. Dry-run by default."
    )
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--confirmed-project-display-name", default=None)
    parser.add_argument("--confirmed-public-slug", default=None)
    parser.add_argument("--confirmed-by", default=None)
    parser.add_argument("--decision-notes", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    # Defensive: these must NEVER be used by this script. Their presence is an immediate refusal.
    parser.add_argument("--enable-send", action="store_true", help="(refused) confirmation never enables sending")
    parser.add_argument("--enable-publish", action="store_true", help="(refused) confirmation never enables publishing")
    parser.add_argument("--mark-ready-for-launch-push", action="store_true", help="(refused) confirmation never marks launch ready")
    args = parser.parse_args()

    print(f"DLF project identity confirmation. launch_key={args.launch_key}. Counts only; no personal data.")

    # Hard refusals (out-of-scope activation attempts) — checked first.
    if args.enable_send or args.enable_publish or args.mark_ready_for_launch_push:
        print("Refusing: this script never enables send/publish or marks ready_for_launch_push.")
        return 1

    name = (args.confirmed_project_display_name or "").strip()
    by = (args.confirmed_by or "").strip()
    if not name:
        print("Refusing: --confirmed-project-display-name is required (operator must supply the confirmed public name).")
        print("No confirmed name supplied -> project_name_confirmed remains a blocker. Nothing was changed.")
        return 1
    if not by:
        print("Refusing: --confirmed-by is required.")
        return 1

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 4:
        print("Refusing: probe returned no usable result.")
        return 1
    exists = int(f[0] or 0)
    already_confirmed = f[1].strip() == "true"
    readiness_open = int(f[2] or 0)
    task_open = int(f[3] or 0)

    if exists != 1:
        print("Refusing: launch project not found for this launch_key.")
        return 1
    if already_confirmed:
        print("Refusing: project name is already confirmed. Revert first (revert_dlf_project_identity_confirmation.py) to re-confirm.")
        return 1

    print("intended transitions:")
    print(f"  launch_projects.project_display_name -> confirmed value (1)")
    print("  launch_projects.raw_context: project_name_confirmed=true, confirmed_by, confirmed_at, previous_display_name, slug")
    print(f"  launch_readiness_checks[project_name_confirmed]: -> passed ({readiness_open})")
    print(f"  launch_operator_tasks[verify_project_name]: -> done ({task_open})")
    print("  send_enabled / publish_enabled / contacts / templates: UNTOUCHED")
    print("  in-transaction guard: rolls back if any send/publish/launch flag would flip")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key, name, args.confirmed_public_slug, by, args.decision_notes))
    print("Confirmation applied:" if code == 0 else "Confirmation FAILED (rolled back):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
