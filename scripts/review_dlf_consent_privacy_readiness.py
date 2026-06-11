#!/usr/bin/env python3
"""Phase 7.8 — DLF consent / suppression / lead-privacy PROCESS review. Dry-run by default.

Reviews the process-level consent/privacy posture and records audit decisions WITHOUT ever
granting a contact permission, approving a contact for campaign, passing WhatsApp provider
approval, or enabling send/publish. Three opt-in actions:

  --approve-lead-form-privacy-process
      If the lead form has consent fields AND PII field mappings exist AND no live lead capture
      is enabled AND --decision-notes is given, mark the lead_privacy_reviewed readiness check
      PASSED and log the consent / privacy-field-mapping process as process_approved. Otherwise it
      logs needs_more_info and leaves the check pending.
  --approve-suppression-process
      Log the suppression-check PROCESS as process_approved. It does NOT pass the suppression_checked
      readiness gate — actually running suppression against contacts is a separate, later step.
  --mark-contact-permissions-needs-review
      Move whatsapp/email permission review items with NO explicit allowed channel_permissions
      record to needs_more_info, set consent_ready to needs_review (never passed, because no
      explicit consent basis exists), and log the contact-permission queue as needs_more_info.

It never inserts a channel_permissions 'allowed' row, never sets a candidate to
approved_for_segment, never passes whatsapp_template_approved, and an in-transaction guard rolls
everything back if any of those — or any send/publish/n8n activation — would happen.

Writing requires BOTH --real-ok and --apply. Counts only; never prints contact values.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PERMISSION_TYPES = ("whatsapp_permission_review", "email_permission_review")


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


def permission_types_sql() -> str:
    return ", ".join(sql_literal(t) for t in PERMISSION_TYPES)


def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk})
SELECT
  (SELECT count(*) FROM launch_lead_capture_forms WHERE launch_project_id IN (SELECT id FROM proj)),
  (SELECT COALESCE(sum(jsonb_array_length(COALESCE(consent_fields,'[]'::jsonb))),0) FROM launch_lead_capture_forms WHERE launch_project_id IN (SELECT id FROM proj)),
  (SELECT count(*) FROM launch_lead_field_mappings WHERE launch_project_id IN (SELECT id FROM proj) AND pii_type IN ('name','email','phone')),
  (SELECT count(*) FROM channel_permissions WHERE permission_status = 'allowed'),
  COALESCE((SELECT ready_for_live_lead_capture::text FROM vw_dlf_lead_intake_readiness WHERE launch_key = {lk}), 'false'),
  (SELECT count(*) FROM launch_contact_permission_review_items ri WHERE ri.launch_project_id IN (SELECT id FROM proj)
     AND ri.review_type IN ({permission_types_sql()}) AND ri.status = 'pending'
     AND NOT EXISTS (SELECT 1 FROM channel_permissions cp WHERE cp.contact_id = ri.contact_id AND cp.permission_status = 'allowed')),
  COALESCE((SELECT check_status FROM launch_readiness_checks r WHERE r.launch_project_id IN (SELECT id FROM proj) AND r.check_type = 'consent_ready' ORDER BY r.created_at LIMIT 1), 'pending'),
  COALESCE((SELECT check_status FROM launch_readiness_checks r WHERE r.launch_project_id IN (SELECT id FROM proj) AND r.check_type = 'lead_privacy_reviewed' ORDER BY r.created_at LIMIT 1), 'pending');
"""


def apply_sql(launch_key, reviewed_by, decision_notes, do_form, form_eligible,
              do_suppression, do_permissions, limit):
    lk = sql_literal(launch_key)
    rb = sql_literal(reviewed_by)
    dn = sql_literal(decision_notes)
    perm_id_limit = ""
    if limit:
        perm_id_limit = f"""
  AND ri.id IN (
    SELECT ri2.id FROM launch_contact_permission_review_items ri2
    JOIN launch_projects p2 ON p2.id = ri2.launch_project_id
    WHERE p2.launch_key = {lk} AND ri2.review_type IN ({permission_types_sql()}) AND ri2.status = 'pending'
      AND NOT EXISTS (SELECT 1 FROM channel_permissions cp WHERE cp.contact_id = ri2.contact_id AND cp.permission_status = 'allowed')
    ORDER BY ri2.created_at LIMIT {int(limit)}
  )"""

    blocks = ["BEGIN;"]

    if do_form:
        if form_eligible:
            blocks.append(f"""
UPDATE launch_readiness_checks r SET
  check_status = 'passed',
  safe_summary = 'Lead-form privacy process reviewed: consent fields + PII field mappings present; no live capture enabled.',
  raw_context = r.raw_context || jsonb_build_object('phase','7.8','phase_7_8_action','lead_privacy_passed','phase_7_8_prev_status', r.check_status),
  updated_at = now()
FROM launch_projects p
WHERE p.id = r.launch_project_id AND p.launch_key = {lk} AND r.check_type = 'lead_privacy_reviewed' AND r.check_status <> 'passed';

INSERT INTO launch_consent_privacy_review_log (launch_project_id, review_area, review_status, reviewed_by, reviewed_at, safe_summary, decision_notes, raw_context)
SELECT p.id, a.area, 'process_approved', {rb}, now(), 'Process-level review of lead-form consent / PII field mappings.', {dn},
       jsonb_build_object('phase','7.8','source','phase_7_8_consent_privacy_review')
FROM launch_projects p, (VALUES ('lead_form_consent'), ('privacy_field_mapping')) AS a(area)
WHERE p.launch_key = {lk};
""")
        else:
            blocks.append(f"""
INSERT INTO launch_consent_privacy_review_log (launch_project_id, review_area, review_status, reviewed_by, reviewed_at, safe_summary, decision_notes, raw_context)
SELECT p.id, 'lead_form_consent', 'needs_more_info', {rb}, now(), 'Lead-form privacy process NOT yet approvable (missing consent fields / PII mappings / live capture must be off / notes required).', {dn},
       jsonb_build_object('phase','7.8','source','phase_7_8_consent_privacy_review')
FROM launch_projects p WHERE p.launch_key = {lk};
""")

    if do_suppression:
        blocks.append(f"""
INSERT INTO launch_consent_privacy_review_log (launch_project_id, review_area, review_status, reviewed_by, reviewed_at, safe_summary, decision_notes, raw_context)
SELECT p.id, 'suppression_process', 'process_approved', {rb}, now(), 'Suppression-check PROCESS approved (execution against contacts is a separate later step; suppression_checked gate NOT passed).', {dn},
       jsonb_build_object('phase','7.8','source','phase_7_8_consent_privacy_review')
FROM launch_projects p WHERE p.launch_key = {lk};
""")

    if do_permissions:
        blocks.append(f"""
UPDATE launch_contact_permission_review_items ri SET
  status = 'needs_more_info', reviewed_by = {rb}, reviewed_at = now(), decision_notes = {dn},
  raw_context = ri.raw_context || jsonb_build_object('phase','7.8','phase_7_8_action','permission_needs_more_info','phase_7_8_prev_status', ri.status),
  updated_at = now()
FROM launch_projects p
WHERE p.id = ri.launch_project_id AND p.launch_key = {lk}
  AND ri.review_type IN ({permission_types_sql()}) AND ri.status = 'pending'
  AND NOT EXISTS (SELECT 1 FROM channel_permissions cp WHERE cp.contact_id = ri.contact_id AND cp.permission_status = 'allowed')
  {perm_id_limit};

UPDATE launch_readiness_checks r SET
  check_status = 'needs_review',
  safe_summary = 'Consent reviewed at process level; BLOCKED — no explicit channel_permissions allowed basis exists.',
  raw_context = r.raw_context || jsonb_build_object('phase','7.8','phase_7_8_action','consent_ready_needs_review','phase_7_8_prev_status', r.check_status),
  updated_at = now()
FROM launch_projects p
WHERE p.id = r.launch_project_id AND p.launch_key = {lk} AND r.check_type = 'consent_ready' AND r.check_status = 'pending'
  AND (SELECT count(*) FROM channel_permissions cp WHERE cp.permission_status = 'allowed') = 0;

INSERT INTO launch_consent_privacy_review_log (launch_project_id, review_area, review_status, reviewed_by, reviewed_at, safe_summary, decision_notes, raw_context)
SELECT p.id, 'contact_permission_queue', 'needs_more_info', {rb}, now(), 'Contact permission queue: explicit opt-in / channel_permissions required before any contact use.', {dn},
       jsonb_build_object('phase','7.8','source','phase_7_8_consent_privacy_review')
FROM launch_projects p WHERE p.launch_key = {lk};
""")

    # Hard guardrail.
    blocks.append(f"""
DO $GUARD$
DECLARE se int; pe int; an int; rf boolean; cpa int; aff int; cr text; wt text;
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
  SELECT ready_for_launch_push INTO rf FROM vw_dlf_launch_priority_dashboard WHERE launch_key = {lk};
  SELECT count(*) FROM channel_permissions WHERE permission_status = 'allowed' INTO cpa;
  SELECT count(*) FROM launch_contact_segment_candidates c JOIN launch_projects p ON p.id = c.launch_project_id
    WHERE p.launch_key = {lk} AND c.candidate_status = 'approved_for_segment' INTO aff;
  SELECT check_status FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id
    WHERE p.launch_key = {lk} AND r.check_type = 'consent_ready' ORDER BY r.created_at LIMIT 1 INTO cr;
  SELECT check_status FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id
    WHERE p.launch_key = {lk} AND r.check_type = 'whatsapp_template_approved' ORDER BY r.created_at LIMIT 1 INTO wt;
  IF se > 0 OR pe > 0 OR an > 0 THEN RAISE EXCEPTION 'Refusing: send/publish/n8n activation (send=%, publish=%, n8n=%).', se, pe, an; END IF;
  IF rf THEN RAISE EXCEPTION 'Refusing: ready_for_launch_push would be true.'; END IF;
  IF cpa > 0 THEN RAISE EXCEPTION 'Refusing: channel_permissions allowed must remain 0 this phase (got %).', cpa; END IF;
  IF aff > 0 THEN RAISE EXCEPTION 'Refusing: no candidate may be approved_for_segment this phase (got %).', aff; END IF;
  IF cr = 'passed' THEN RAISE EXCEPTION 'Refusing: consent_ready must not be passed (no explicit consent basis).'; END IF;
  IF wt = 'passed' THEN RAISE EXCEPTION 'Refusing: whatsapp_template_approved must not be passed (provider approval is external).'; END IF;
END $GUARD$;
COMMIT;

SELECT 'log_rows_phase_7_8', count(*)::text FROM launch_consent_privacy_review_log lg
  JOIN launch_projects p ON p.id = lg.launch_project_id WHERE p.launch_key = {lk} AND lg.raw_context->>'phase' = '7.8'
UNION ALL SELECT 'lead_privacy_reviewed', check_status FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id WHERE p.launch_key = {lk} AND r.check_type = 'lead_privacy_reviewed'
UNION ALL SELECT 'consent_ready', check_status FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id WHERE p.launch_key = {lk} AND r.check_type = 'consent_ready'
UNION ALL SELECT 'whatsapp_template_approved', check_status FROM launch_readiness_checks r JOIN launch_projects p ON p.id = r.launch_project_id WHERE p.launch_key = {lk} AND r.check_type = 'whatsapp_template_approved'
UNION ALL SELECT 'permission_reviews_needs_more_info', count(*)::text FROM launch_contact_permission_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.status = 'needs_more_info' AND ri.raw_context->>'phase' = '7.8'
UNION ALL SELECT 'candidates_approved_for_segment', count(*)::text FROM launch_contact_segment_candidates c JOIN launch_projects p ON p.id = c.launch_project_id WHERE p.launch_key = {lk} AND c.candidate_status = 'approved_for_segment'
UNION ALL SELECT 'channel_permissions_allowed', count(*)::text FROM channel_permissions WHERE permission_status = 'allowed'
UNION ALL SELECT 'send_enabled_count', send_enabled_count::text FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
UNION ALL SELECT 'publish_enabled_count', publish_enabled_count::text FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
UNION ALL SELECT 'safety_status', safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_launch_push', ready_for_launch_push::text FROM vw_dlf_launch_priority_dashboard WHERE launch_key = {lk}
ORDER BY 1;
""")
    return "\n".join(blocks)


def main() -> int:
    parser = argparse.ArgumentParser(description="DLF consent/suppression/lead-privacy process review. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--reviewed-by", default=None)
    parser.add_argument("--decision-notes", default=None)
    parser.add_argument("--approve-lead-form-privacy-process", action="store_true")
    parser.add_argument("--approve-suppression-process", action="store_true")
    parser.add_argument("--mark-contact-permissions-needs-review", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    # Defensive: always refused.
    parser.add_argument("--enable-send", action="store_true")
    parser.add_argument("--enable-publish", action="store_true")
    parser.add_argument("--approve-contacts-for-campaign", action="store_true")
    parser.add_argument("--mark-permission-allowed", action="store_true")
    parser.add_argument("--pass-whatsapp-template-approval", action="store_true")
    args = parser.parse_args()

    print(f"DLF consent/privacy process review. launch_key={args.launch_key}. Counts only; no contact values.")

    if args.enable_send or args.enable_publish or args.approve_contacts_for_campaign or args.mark_permission_allowed or args.pass_whatsapp_template_approval:
        print("Refusing: this script never enables send/publish, approves contacts for campaign, "
              "marks a permission allowed, or passes WhatsApp provider approval.")
        return 1

    do_form = args.approve_lead_form_privacy_process
    do_suppression = args.approve_suppression_process
    do_permissions = args.mark_contact_permissions_needs_review
    if not (do_form or do_suppression or do_permissions):
        print("Nothing to do: pass at least one of --approve-lead-form-privacy-process, "
              "--approve-suppression-process, --mark-contact-permissions-needs-review.")
        return 1

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 8:
        print("Refusing: probe returned no usable result.")
        return 1
    lead_form_count, consent_fields, pii_mappings = int(f[0] or 0), int(f[1] or 0), int(f[2] or 0)
    channel_perms_allowed = int(f[3] or 0)
    live_capture = f[4].strip() == "true"
    perm_unknown = int(f[5] or 0)
    consent_status, lead_privacy_status = f[6].strip(), f[7].strip()

    has_notes = bool((args.decision_notes or "").strip())
    form_eligible = (lead_form_count >= 1 and consent_fields > 0 and pii_mappings > 0
                     and not live_capture and has_notes)

    print("inputs (counts only):")
    print(f"  lead forms: {lead_form_count}   consent fields: {consent_fields}   PII field mappings: {pii_mappings}")
    print(f"  channel_permissions allowed: {channel_perms_allowed}   live lead capture: {live_capture}")
    print(f"  whatsapp/email permission reviews with NO allowed record: {perm_unknown}")
    print(f"  consent_ready={consent_status}   lead_privacy_reviewed={lead_privacy_status}")
    print("projected actions:")
    if do_form:
        print(f"  lead-form privacy process: {'ELIGIBLE -> would PASS lead_privacy_reviewed + log process_approved' if form_eligible else 'NOT eligible -> would log needs_more_info, leave check pending'}")
    if do_suppression:
        print("  suppression process: would log process_approved (suppression_checked gate NOT passed)")
    if do_permissions:
        n = min(perm_unknown, args.limit) if args.limit else perm_unknown
        print(f"  contact permissions: {n} whatsapp/email review item(s) -> needs_more_info; consent_ready -> needs_review (never passed)")
    print("  contacts approved for campaign: 0 (never)   channel permission allowed: never granted")
    print("  whatsapp_template_approved: untouched (stays pending)   send/publish: untouched")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key, args.reviewed_by, args.decision_notes,
                                      do_form, form_eligible, do_suppression, do_permissions, args.limit))
    print("Consent/privacy review applied:" if code == 0 else "Consent/privacy review FAILED (rolled back):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
