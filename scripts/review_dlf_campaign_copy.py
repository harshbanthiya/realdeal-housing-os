#!/usr/bin/env python3
"""Phase 7.7 — internal DLF Westpark campaign copy + consent-language review. Dry-run by default.

Three safe, reversible internal actions (each gated behind its own flag):
  --replace-project-name-placeholders
      Replace the confirmed project-name placeholder [PROJECT_NAME_CONFIRM] -> "DLF Westpark"
      in DRAFT text fields of message templates, social drafts, and the landing page spec.
      Factual placeholders ([RERA_VERIFY], [PRICE_VERIFY], [BROCHURE_LINK_PENDING],
      [WIX_PAGE_PENDING], [VERIFY], [VISUAL_DIRECTION_PENDING], any [*_VERIFY]/[*_PENDING])
      are KEPT untouched.
  --approve-safe-internal-copy
      Set copy/consent review items whose linked copy has NO remaining factual placeholder to
      status='approved' (internal copy review only — NOT provider approval, NOT a send/publish gate).
  --mark-unverified-factual-claims-needs-more-info
      Set copy review items whose linked copy STILL contains a factual placeholder to
      status='needs_more_info'.

It writes ONLY launch_message_templates / launch_social_content_drafts / launch_landing_page_specs
text + raw_context, and launch_draft_review_items review marks. It NEVER enables send/publish,
NEVER passes any launch_readiness_check (so whatsapp_template_approved stays pending — provider
approval is out of scope), NEVER touches contacts / permission reviews / leads, and a hard
in-transaction guard rolls everything back if any send/publish/n8n flag would flip.

Writing requires BOTH --real-ok and --apply. Counts only; never prints copy bodies or personal data.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROJECT_NAME_TOKEN = "[PROJECT_NAME_CONFIRM]"
CONFIRMED_NAME = "DLF Westpark"
COPY_REVIEW_TYPES = (
    "whatsapp_copy_review", "email_copy_review", "social_copy_review",
    "compliance_review", "consent_review",
)
# A factual/production placeholder still needing verification: any [..._VERIFY] / [..._PENDING]
# / bare [VERIFY]. The project-name token ends in CONFIRM, so it is excluded by design.
FACTUAL_RE = r"\[[A-Z0-9_]*(VERIFY|PENDING)\]"

# has_unverified for a review item, based on its linked content's text fields.
HAS_UNVERIFIED = (
    "CASE "
    "WHEN ri.message_template_id IS NOT NULL THEN "
    "(SELECT (coalesce(t.subject,'')||' '||coalesce(t.body,'')||' '||coalesce(t.cta,'')) ~ '" + FACTUAL_RE + "' "
    "FROM launch_message_templates t WHERE t.id = ri.message_template_id) "
    "WHEN ri.social_content_draft_id IS NOT NULL THEN "
    "(SELECT (coalesce(s.hook,'')||' '||coalesce(s.caption,'')||' '||coalesce(s.cta,'')||' '||coalesce(s.hashtags,'')||' '||coalesce(s.visual_direction,'')) ~ '" + FACTUAL_RE + "' "
    "FROM launch_social_content_drafts s WHERE s.id = ri.social_content_draft_id) "
    "WHEN ri.landing_page_spec_id IS NOT NULL THEN "
    "(SELECT (coalesce(l.page_title,'')||' '||coalesce(l.hero_headline,'')||' '||coalesce(l.hero_subheadline,'')||' '||coalesce(l.primary_cta,'')||' '||coalesce(l.secondary_cta,'')) ~ '" + FACTUAL_RE + "' "
    "FROM launch_landing_page_specs l WHERE l.id = ri.landing_page_spec_id) "
    "ELSE false END"
)
def review_types_sql() -> str:
    return ", ".join(sql_literal(t) for t in COPY_REVIEW_TYPES)

def probe_sql(launch_key: str, limit: int | None) -> str:
    lk = sql_literal(launch_key)
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    token = sql_literal("%" + PROJECT_NAME_TOKEN + "%")
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
scope AS (
  SELECT ri.id, ({HAS_UNVERIFIED}) AS hv
  FROM launch_draft_review_items ri
  WHERE ri.launch_project_id IN (SELECT id FROM proj)
    AND ri.status = 'pending'
    AND ri.review_type IN ({review_types_sql()})
  ORDER BY ri.created_at
  {limit_clause}
)
SELECT
  (SELECT count(*) FROM launch_message_templates WHERE launch_project_id IN (SELECT id FROM proj)),
  (SELECT count(*) FROM launch_social_content_drafts WHERE launch_project_id IN (SELECT id FROM proj)),
  (SELECT count(*) FROM launch_message_templates WHERE launch_project_id IN (SELECT id FROM proj)
     AND (subject LIKE {token} OR body LIKE {token} OR cta LIKE {token})),
  (SELECT count(*) FROM launch_social_content_drafts WHERE launch_project_id IN (SELECT id FROM proj)
     AND (hook LIKE {token} OR caption LIKE {token} OR cta LIKE {token} OR hashtags LIKE {token} OR visual_direction LIKE {token})),
  (SELECT count(*) FROM launch_landing_page_specs WHERE launch_project_id IN (SELECT id FROM proj)
     AND (page_title LIKE {token} OR hero_headline LIKE {token} OR hero_subheadline LIKE {token} OR primary_cta LIKE {token} OR secondary_cta LIKE {token})),
  (SELECT count(*) FROM scope),
  (SELECT count(*) FROM scope WHERE hv = false),
  (SELECT count(*) FROM scope WHERE hv = true);
"""

def apply_sql(launch_key, reviewed_by, decision_notes, do_replace, do_approve, do_needs_info, limit):
    tmpl = """
BEGIN;
__REPLACE_BLOCK__
CREATE TEMP TABLE tmp_scope AS
SELECT ri.id, ri.message_template_id, ri.social_content_draft_id, ri.landing_page_spec_id,
       (__HV__) AS has_unverified
FROM launch_draft_review_items ri
WHERE ri.launch_project_id IN (SELECT id FROM launch_projects WHERE launch_key = __LK__)
  AND ri.status = 'pending'
  AND ri.review_type IN (__RTYPES__)
ORDER BY ri.created_at
__LIMIT__;

__APPROVE_BLOCK__
__NEEDS_BLOCK__
__STAMP_BLOCK__
-- Hard guardrail: copy review may NEVER enable sending/publishing/n8n activation.
DO $GUARD$
DECLARE se int; pe int; an int;
BEGIN
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN launch_projects p ON p.id = lc.launch_project_id WHERE p.launch_key = __LK__ AND lc.send_enabled)
    + (SELECT count(*) FROM launch_message_templates m JOIN launch_projects p ON p.id = m.launch_project_id WHERE p.launch_key = __LK__ AND m.send_enabled)
    + (SELECT count(*) FROM launch_campaign_calendar cc JOIN launch_projects p ON p.id = cc.launch_project_id WHERE p.launch_key = __LK__ AND cc.send_enabled)
  INTO se;
  SELECT
      (SELECT count(*) FROM launch_channels lc JOIN launch_projects p ON p.id = lc.launch_project_id WHERE p.launch_key = __LK__ AND lc.publish_enabled)
    + (SELECT count(*) FROM launch_landing_page_specs s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = __LK__ AND s.publish_enabled)
    + (SELECT count(*) FROM launch_lead_capture_forms f JOIN launch_projects p ON p.id = f.launch_project_id WHERE p.launch_key = __LK__ AND f.publish_enabled)
    + (SELECT count(*) FROM launch_social_content_drafts sc JOIN launch_projects p ON p.id = sc.launch_project_id WHERE p.launch_key = __LK__ AND sc.publish_enabled)
  INTO pe;
  SELECT count(*) FROM launch_n8n_workflow_blueprints b JOIN launch_projects p ON p.id = b.launch_project_id
    WHERE p.launch_key = __LK__ AND (b.workflow_status = 'active' OR b.activation_status = 'active') INTO an;
  IF se > 0 OR pe > 0 OR an > 0 THEN
    RAISE EXCEPTION 'Refusing: activation flag detected (send=%, publish=%, active_n8n=%).', se, pe, an;
  END IF;
END $GUARD$;
COMMIT;

SELECT 'review_items_approved', count(*)::text FROM launch_draft_review_items ri
  JOIN launch_projects p ON p.id = ri.launch_project_id
  WHERE p.launch_key = __LK__ AND ri.review_type IN (__RTYPES__)
    AND ri.status = 'approved' AND ri.raw_context->>'phase' = '7.7'
UNION ALL SELECT 'review_items_needs_more_info', count(*)::text FROM launch_draft_review_items ri
  JOIN launch_projects p ON p.id = ri.launch_project_id
  WHERE p.launch_key = __LK__ AND ri.review_type IN (__RTYPES__)
    AND ri.status = 'needs_more_info' AND ri.raw_context->>'phase' = '7.7'
UNION ALL SELECT 'project_name_token_remaining_templates', count(*)::text FROM launch_message_templates
  WHERE launch_project_id IN (SELECT id FROM launch_projects WHERE launch_key = __LK__)
    AND (subject LIKE __TOKEN__ OR body LIKE __TOKEN__ OR cta LIKE __TOKEN__)
UNION ALL SELECT 'project_name_token_remaining_social', count(*)::text FROM launch_social_content_drafts
  WHERE launch_project_id IN (SELECT id FROM launch_projects WHERE launch_key = __LK__)
    AND (hook LIKE __TOKEN__ OR caption LIKE __TOKEN__ OR cta LIKE __TOKEN__ OR hashtags LIKE __TOKEN__ OR visual_direction LIKE __TOKEN__)
UNION ALL SELECT 'send_enabled_count', send_enabled_count::text FROM vw_dlf_operator_safety_posture WHERE launch_key = __LK__
UNION ALL SELECT 'publish_enabled_count', publish_enabled_count::text FROM vw_dlf_operator_safety_posture WHERE launch_key = __LK__
UNION ALL SELECT 'safety_status', safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = __LK__
UNION ALL SELECT 'ready_for_launch_push', ready_for_launch_push::text FROM vw_dlf_launch_priority_dashboard WHERE launch_key = __LK__
ORDER BY 1;
"""

    lk = sql_literal(launch_key)
    rb = sql_literal(reviewed_by)
    dn = sql_literal(decision_notes)
    token = sql_literal("%" + PROJECT_NAME_TOKEN + "%")
    repl_args = (sql_literal(PROJECT_NAME_TOKEN), sql_literal(CONFIRMED_NAME))

    replace_block = ""
    if do_replace:
        rep_marker = ("jsonb_build_object('phase_7_7_project_name_replaced', true, "
                      "'phase_7_7_project_name_value', " + sql_literal(CONFIRMED_NAME) + ")")
        replace_block = f"""
UPDATE launch_message_templates t SET
  subject = replace(t.subject, {repl_args[0]}, {repl_args[1]}),
  body    = replace(t.body,    {repl_args[0]}, {repl_args[1]}),
  cta     = replace(t.cta,     {repl_args[0]}, {repl_args[1]}),
  raw_context = coalesce(t.raw_context, '{{}}'::jsonb) || {rep_marker},
  updated_at = now()
FROM launch_projects p
WHERE p.id = t.launch_project_id AND p.launch_key = {lk}
  AND (t.subject LIKE {token} OR t.body LIKE {token} OR t.cta LIKE {token});

UPDATE launch_social_content_drafts s SET
  hook = replace(s.hook, {repl_args[0]}, {repl_args[1]}),
  caption = replace(s.caption, {repl_args[0]}, {repl_args[1]}),
  cta = replace(s.cta, {repl_args[0]}, {repl_args[1]}),
  hashtags = replace(s.hashtags, {repl_args[0]}, {repl_args[1]}),
  visual_direction = replace(s.visual_direction, {repl_args[0]}, {repl_args[1]}),
  raw_context = coalesce(s.raw_context, '{{}}'::jsonb) || {rep_marker},
  updated_at = now()
FROM launch_projects p
WHERE p.id = s.launch_project_id AND p.launch_key = {lk}
  AND (s.hook LIKE {token} OR s.caption LIKE {token} OR s.cta LIKE {token} OR s.hashtags LIKE {token} OR s.visual_direction LIKE {token});

UPDATE launch_landing_page_specs l SET
  page_title = replace(l.page_title, {repl_args[0]}, {repl_args[1]}),
  hero_headline = replace(l.hero_headline, {repl_args[0]}, {repl_args[1]}),
  hero_subheadline = replace(l.hero_subheadline, {repl_args[0]}, {repl_args[1]}),
  primary_cta = replace(l.primary_cta, {repl_args[0]}, {repl_args[1]}),
  secondary_cta = replace(l.secondary_cta, {repl_args[0]}, {repl_args[1]}),
  raw_context = coalesce(l.raw_context, '{{}}'::jsonb) || {rep_marker},
  updated_at = now()
FROM launch_projects p
WHERE p.id = l.launch_project_id AND p.launch_key = {lk}
  AND (l.page_title LIKE {token} OR l.hero_headline LIKE {token} OR l.hero_subheadline LIKE {token} OR l.primary_cta LIKE {token} OR l.secondary_cta LIKE {token});
"""

    approve_block = ""
    if do_approve:
        approve_block = f"""
UPDATE launch_draft_review_items ri SET
  status = 'approved', reviewed_by = {rb}, reviewed_at = now(), decision_notes = {dn},
  raw_context = coalesce(ri.raw_context, '{{}}'::jsonb)
    || jsonb_build_object('phase', '7.7', 'phase_7_7_action', 'approved_internal_copy', 'phase_7_7_prev_status', 'pending'),
  updated_at = now()
FROM tmp_scope sc WHERE sc.id = ri.id AND sc.has_unverified = false;
"""

    needs_block = ""
    if do_needs_info:
        needs_block = f"""
UPDATE launch_draft_review_items ri SET
  status = 'needs_more_info', reviewed_by = {rb}, reviewed_at = now(), decision_notes = {dn},
  raw_context = coalesce(ri.raw_context, '{{}}'::jsonb)
    || jsonb_build_object('phase', '7.7', 'phase_7_7_action', 'needs_more_info_factual', 'phase_7_7_prev_status', 'pending'),
  updated_at = now()
FROM tmp_scope sc WHERE sc.id = ri.id AND sc.has_unverified = true;
"""

    # Stamp linked content as internally copy-reviewed for items that passed internal review.
    stamp_block = ""
    if do_approve:
        stamp_marker = "jsonb_build_object('internal_copy_reviewed', true, 'phase_7_7_internal_copy_reviewed', true)"
        stamp_block = f"""
UPDATE launch_message_templates t SET
  raw_context = coalesce(t.raw_context, '{{}}'::jsonb) || {stamp_marker}, updated_at = now()
FROM tmp_scope sc WHERE sc.message_template_id = t.id AND sc.has_unverified = false;

UPDATE launch_social_content_drafts s SET
  raw_context = coalesce(s.raw_context, '{{}}'::jsonb) || {stamp_marker}, updated_at = now()
FROM tmp_scope sc WHERE sc.social_content_draft_id = s.id AND sc.has_unverified = false;
"""

    sql = tmpl
    sql = sql.replace("__REPLACE_BLOCK__", replace_block)
    sql = sql.replace("__APPROVE_BLOCK__", approve_block)
    sql = sql.replace("__NEEDS_BLOCK__", needs_block)
    sql = sql.replace("__STAMP_BLOCK__", stamp_block)
    sql = sql.replace("__HV__", HAS_UNVERIFIED)
    sql = sql.replace("__RTYPES__", review_types_sql())
    sql = sql.replace("__LIMIT__", f"LIMIT {int(limit)}" if limit else "")
    sql = sql.replace("__TOKEN__", token)
    sql = sql.replace("__LK__", lk)
    return sql

def main() -> int:
    parser = argparse.ArgumentParser(description="Internal DLF campaign copy review. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--reviewed-by", default=None)
    parser.add_argument("--decision-notes", default=None)
    parser.add_argument("--replace-project-name-placeholders", action="store_true")
    parser.add_argument("--approve-safe-internal-copy", action="store_true")
    parser.add_argument("--mark-unverified-factual-claims-needs-more-info", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    # Defensive: these are always refused — copy review never does any of them.
    parser.add_argument("--enable-send", action="store_true")
    parser.add_argument("--enable-publish", action="store_true")
    parser.add_argument("--mark-ready-for-launch-push", action="store_true")
    parser.add_argument("--pass-whatsapp-provider-approval", action="store_true")
    args = parser.parse_args()

    print(f"DLF campaign copy review. launch_key={args.launch_key}. Counts only; no copy bodies / no personal data.")

    if args.enable_send or args.enable_publish or args.mark_ready_for_launch_push or args.pass_whatsapp_provider_approval:
        print("Refusing: copy review never enables send/publish, marks ready_for_launch_push, or passes WhatsApp provider approval.")
        return 1

    do_replace = args.replace_project_name_placeholders
    do_approve = args.approve_safe_internal_copy
    do_needs_info = args.mark_unverified_factual_claims_needs_more_info
    if not (do_replace or do_approve or do_needs_info):
        print("Nothing to do: pass at least one of --replace-project-name-placeholders, "
              "--approve-safe-internal-copy, --mark-unverified-factual-claims-needs-more-info.")
        return 1

    code, probe = run_psql(probe_sql(args.launch_key, args.limit))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 8:
        print("Refusing: probe returned no usable result.")
        return 1
    templates_total, social_total = int(f[0] or 0), int(f[1] or 0)
    tmpl_with_token, social_with_token, landing_with_token = int(f[2] or 0), int(f[3] or 0), int(f[4] or 0)
    scope_total, would_approve, would_needs = int(f[5] or 0), int(f[6] or 0), int(f[7] or 0)

    print("projected (dry-run) counts:")
    print(f"  templates inspected: {templates_total}")
    print(f"  social drafts inspected: {social_total}")
    print(f"  rows with {PROJECT_NAME_TOKEN} -> templates {tmpl_with_token}, social {social_with_token}, landing {landing_with_token}"
          + ("  [replace ON]" if do_replace else "  [replace OFF]"))
    print(f"  copy/consent review items in scope (pending): {scope_total}")
    print(f"  -> would approve (no factual placeholder): {would_approve}" + ("" if do_approve else "  [approve OFF]"))
    print(f"  -> would mark needs_more_info (has factual placeholder): {would_needs}" + ("" if do_needs_info else "  [needs_more_info OFF]"))
    print("  send_enabled changes: 0   publish_enabled changes: 0   (never modified)")
    print("  launch_readiness_checks (incl. whatsapp_template_approved): UNTOUCHED — provider approval not granted")
    print("  contacts / permission reviews / leads: UNTOUCHED")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key, args.reviewed_by, args.decision_notes,
                                      do_replace, do_approve, do_needs_info, args.limit))
    print("Copy review applied:" if code == 0 else "Copy review FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
