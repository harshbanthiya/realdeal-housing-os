#!/usr/bin/env python3
"""Phase 7.20 — record manual Wix staging build progress for DLF Westpark. Dry-run by default.

Tracks the HUMAN/manual Wix staging build: whether an operator manually created a staging/preview
site, optional staging name/URL, moving selected setup/safety checklist and QA items forward, and
an explicit note that Wix API permission/key usage is DEFERRED to a later capability-map phase.

It performs NO Wix API call, NEVER reads or stores a Wix API key, NEVER inspects .env for Wix
secrets (it only reads Postgres connection values to talk to the local DB), and never connects a
domain, enables indexing, publishes a page, creates a live form/webhook, enables tracking, enables
send/publish, or creates leads/contacts. Every staging live flag stays false. An in-transaction
guard rolls everything back if any of those would change.

Writing requires BOTH --real-ok and --apply. Counts only; never prints secrets or contact values.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.20"
SOURCE = "dlf_wix_staging_build_tracking"
PLAN_PHASE = "7.19"  # the seeded staging plan rows we advance

SETUP_CATEGORIES = ("setup",)
SHELL_CATEGORIES = ("hero", "navigation", "content_sections")
SAFETY_CHECKLIST_CATEGORIES = ("safety",)
SAFETY_QA_TYPES = ("domain_not_connected", "noindex", "webhook_disabled", "tracking_disabled")
def project_exists(launch_key: str) -> bool:
    code, output = run_psql(f"SELECT count(*) FROM launch_projects WHERE launch_key = {sql_literal(launch_key)};")
    return code == 0 and output.strip() == "1"

def in_list(col: str, values) -> str:
    return f"{col} IN (" + ", ".join(sql_literal(v) for v in values) + ")"

def ctx(extra: dict | None = None) -> str:
    pairs = [
        "'phase'", f"'{PHASE}'",
        "'source'", f"'{SOURCE}'",
        "'external_calls_made'", "false",
        "'wix_api_call_made'", "false",
        "'wix_api_key_used'", "false",
        "'publish_enabled'", "false",
        "'communication_sent'", "false",
    ]
    if extra:
        for k, v in extra.items():
            pairs.append(sql_literal(k))
            pairs.append(sql_literal(v))
    return "jsonb_build_object(" + ", ".join(pairs) + ")"

def apply_sql(args, do_site: bool) -> str:
    lk = sql_literal(args.launch_key)
    rb = sql_literal(args.performed_by)
    dn = sql_literal(args.decision_notes)
    base = ctx()

    common = f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
site AS (
  SELECT id FROM wix_staging_sites
  WHERE launch_project_id IN (SELECT id FROM proj) AND raw_context->>'phase' = '{PLAN_PHASE}'
  ORDER BY created_at LIMIT 1
)
"""
    blocks = ["BEGIN;"]

    if do_site:
        name_lit = sql_literal(args.staging_site_name)
        url_lit = sql_literal(args.staging_site_url)
        blocks.append(common + f""",
upd AS (
  UPDATE wix_staging_sites s SET
    staging_status = 'created_manually',
    staging_site_name = COALESCE({name_lit}, s.staging_site_name),
    staging_site_url = COALESCE({url_lit}, s.staging_site_url),
    raw_context = s.raw_context || jsonb_build_object('phase_7_20_action','staging_site_reported','phase_7_20_prev_status', s.staging_status),
    updated_at = now()
  WHERE s.id = (SELECT id FROM site)
  RETURNING s.id, (s.raw_context->>'phase_7_20_prev_status') AS old_status, s.staging_status AS new_status
)
INSERT INTO wix_staging_build_action_log
  (launch_project_id, wix_staging_site_id, action_type, old_status, new_status, performed_by, action_notes, raw_context)
SELECT (SELECT id FROM proj), upd.id, 'staging_site_reported', upd.old_status, upd.new_status, {rb}, {dn},
  {ctx({'staging_site_named': bool(args.staging_site_name), 'staging_url_recorded': bool(args.staging_site_url)})}
FROM upd;
""")

    if args.mark_setup_started:
        blocks.append(common + f""",
upd AS (
  UPDATE wix_staging_build_checklist_items c SET
    checklist_status = 'in_progress',
    raw_context = c.raw_context || jsonb_build_object('phase_7_20_action','checklist_started','phase_7_20_prev_status', c.checklist_status),
    updated_at = now()
  WHERE c.launch_project_id IN (SELECT id FROM proj) AND c.raw_context->>'phase' = '{PLAN_PHASE}'
    AND {in_list('c.checklist_category', SETUP_CATEGORIES)} AND c.checklist_status = 'pending'
  RETURNING c.id, (c.raw_context->>'phase_7_20_prev_status') AS old_status, c.checklist_status AS new_status
)
INSERT INTO wix_staging_build_action_log
  (launch_project_id, wix_staging_site_id, checklist_item_id, action_type, old_status, new_status, performed_by, action_notes, raw_context)
SELECT (SELECT id FROM proj), (SELECT id FROM site), upd.id, 'checklist_item_started', upd.old_status, upd.new_status, {rb}, {dn}, {base}
FROM upd;
""")

    if args.mark_gallery_white_shell_started:
        blocks.append(common + f""",
upd AS (
  UPDATE wix_staging_build_checklist_items c SET
    checklist_status = 'in_progress',
    raw_context = c.raw_context || jsonb_build_object('phase_7_20_action','checklist_started','phase_7_20_prev_status', c.checklist_status),
    updated_at = now()
  WHERE c.launch_project_id IN (SELECT id FROM proj) AND c.raw_context->>'phase' = '{PLAN_PHASE}'
    AND {in_list('c.checklist_category', SHELL_CATEGORIES)} AND c.checklist_status = 'pending'
  RETURNING c.id, (c.raw_context->>'phase_7_20_prev_status') AS old_status, c.checklist_status AS new_status
)
INSERT INTO wix_staging_build_action_log
  (launch_project_id, wix_staging_site_id, checklist_item_id, action_type, old_status, new_status, performed_by, action_notes, raw_context)
SELECT (SELECT id FROM proj), (SELECT id FROM site), upd.id, 'checklist_item_started', upd.old_status, upd.new_status, {rb}, {dn}, {base}
FROM upd;
""")

    if args.mark_safety_checks_passed:
        # Safety checklist items -> passed
        blocks.append(common + f""",
upd AS (
  UPDATE wix_staging_build_checklist_items c SET
    checklist_status = 'passed',
    raw_context = c.raw_context || jsonb_build_object('phase_7_20_action','checklist_passed','phase_7_20_prev_status', c.checklist_status),
    updated_at = now()
  WHERE c.launch_project_id IN (SELECT id FROM proj) AND c.raw_context->>'phase' = '{PLAN_PHASE}'
    AND {in_list('c.checklist_category', SAFETY_CHECKLIST_CATEGORIES)} AND c.checklist_status IN ('pending','in_progress')
  RETURNING c.id, (c.raw_context->>'phase_7_20_prev_status') AS old_status, c.checklist_status AS new_status
)
INSERT INTO wix_staging_build_action_log
  (launch_project_id, wix_staging_site_id, checklist_item_id, action_type, old_status, new_status, performed_by, action_notes, raw_context)
SELECT (SELECT id FROM proj), (SELECT id FROM site), upd.id, 'checklist_item_passed', upd.old_status, upd.new_status, {rb}, {dn},
  {ctx({'safety_confirms': 'all_six_off'})}
FROM upd;
""")
        # Safety / absence QA checks -> passed (never visual/content QA)
        blocks.append(common + f""",
upd AS (
  UPDATE wix_staging_qa_checks q SET
    qa_status = 'passed',
    raw_context = q.raw_context || jsonb_build_object('phase_7_20_action','safety_flag_verified','phase_7_20_prev_status', q.qa_status),
    updated_at = now()
  WHERE q.launch_project_id IN (SELECT id FROM proj) AND q.raw_context->>'phase' = '{PLAN_PHASE}'
    AND {in_list('q.qa_type', SAFETY_QA_TYPES)} AND q.qa_status = 'pending'
  RETURNING q.id, (q.raw_context->>'phase_7_20_prev_status') AS old_status, q.qa_status AS new_status
)
INSERT INTO wix_staging_build_action_log
  (launch_project_id, wix_staging_site_id, qa_check_id, action_type, old_status, new_status, performed_by, action_notes, raw_context)
SELECT (SELECT id FROM proj), (SELECT id FROM site), upd.id, 'safety_flag_verified', upd.old_status, upd.new_status, {rb}, {dn},
  {ctx({'safety_confirms': 'all_six_off'})}
FROM upd;
""")

    if args.record_api_permission_review_deferred:
        blocks.append(common + f"""
INSERT INTO wix_staging_build_action_log
  (launch_project_id, wix_staging_site_id, action_type, old_status, new_status, performed_by, action_notes, raw_context)
SELECT (SELECT id FROM proj), (SELECT id FROM site), 'api_permission_review_deferred', NULL, 'deferred', {rb},
  'Operator reviewed Wix API permissions in the Wix dashboard. Wix API permission/key usage is DEFERRED to a later capability-map phase. No API key requested, read, or stored; no external_call_allowed change.',
  {ctx({'api_key_used': False, 'api_key_read': False, 'capability_map': 'deferred'})}
FROM proj;
""")

    # Hard guard — roll back if any live/domain/index/publish/form/webhook/tracking/api flag set,
    # or if leads/contacts/send/publish changed.
    blocks.append(f"""
DO $GUARD$
DECLARE bad int; inbound int; contacts_count int; se int; pe int;
BEGIN
  SELECT count(*) INTO bad FROM wix_staging_sites s JOIN launch_projects p ON p.id = s.launch_project_id
    WHERE p.launch_key = {lk} AND (s.real_domain_connected OR s.public_indexing_enabled OR s.wix_api_call_made
      OR s.page_created OR s.page_published OR s.live_form_created OR s.live_webhook_created OR s.external_tracking_enabled);
  SELECT count(*) INTO inbound FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  SELECT send_enabled_count INTO se FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT publish_enabled_count INTO pe FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  IF bad > 0 THEN RAISE EXCEPTION 'Refusing: a staging site has a live/domain/indexing/publish/form/webhook/tracking/api flag set.'; END IF;
  IF inbound <> 0 THEN RAISE EXCEPTION 'Refusing: inbound lead count changed to %.', inbound; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
  IF se > 0 OR pe > 0 THEN RAISE EXCEPTION 'Refusing: send/publish enabled (send=%, publish=%).', se, pe; END IF;
END $GUARD$;
COMMIT;

SELECT 'staging_status', staging_status FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk}
UNION ALL SELECT 'checklist_started', checklist_started::text FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk}
UNION ALL SELECT 'checklist_passed', checklist_passed::text FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk}
UNION ALL SELECT 'qa_passed', qa_passed::text FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk}
UNION ALL SELECT 'api_permission_review_deferred_count', api_permission_review_deferred_count::text FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk}
UNION ALL SELECT 'action_log_rows', count(*)::text FROM wix_staging_build_action_log l JOIN launch_projects p ON p.id = l.launch_project_id WHERE p.launch_key = {lk} AND l.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'safety_flags_clean', safety_flags_clean::text FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_staging_qa', ready_for_staging_qa::text FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_fake_lead_test', ready_for_fake_lead_test::text FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_production_publish', ready_for_production_publish::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'real_domain_connected_count', real_domain_connected_count::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'page_published_count', page_published_count::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'live_form_created_count', live_form_created_count::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'live_webhook_created_count', live_webhook_created_count::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'inbound_leads', count(*)::text FROM inbound_leads
UNION ALL SELECT 'contacts', count(*)::text FROM contacts
ORDER BY 1;
""")
    return "\n".join(blocks)

def main() -> int:
    parser = argparse.ArgumentParser(description="Record manual Wix staging build progress. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--performed-by", default=None)
    parser.add_argument("--decision-notes", default=None)
    parser.add_argument("--staging-site-name", default=None)
    parser.add_argument("--staging-site-url", default=None)
    parser.add_argument("--confirm-staging-site-created-manually", action="store_true")
    parser.add_argument("--confirm-real-domain-not-connected", action="store_true")
    parser.add_argument("--confirm-public-indexing-disabled", action="store_true")
    parser.add_argument("--confirm-page-not-published", action="store_true")
    parser.add_argument("--confirm-no-live-form", action="store_true")
    parser.add_argument("--confirm-no-live-webhook", action="store_true")
    parser.add_argument("--confirm-no-external-tracking", action="store_true")
    parser.add_argument("--mark-setup-started", action="store_true")
    parser.add_argument("--mark-gallery-white-shell-started", action="store_true")
    parser.add_argument("--mark-safety-checks-passed", action="store_true")
    parser.add_argument("--record-api-permission-review-deferred", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    # Defensive: always refused.
    parser.add_argument("--use-wix-api-key", action="store_true")
    parser.add_argument("--call-wix-api", action="store_true")
    parser.add_argument("--set-real-domain-connected", action="store_true")
    parser.add_argument("--set-public-indexing-enabled", action="store_true")
    parser.add_argument("--set-page-published", action="store_true")
    parser.add_argument("--set-live-form-created", action="store_true")
    parser.add_argument("--set-live-webhook-created", action="store_true")
    parser.add_argument("--set-external-tracking-enabled", action="store_true")
    parser.add_argument("--enable-publish", action="store_true")
    parser.add_argument("--enable-send", action="store_true")
    args = parser.parse_args()

    print(f"DLF Westpark manual Wix staging build tracking. launch_key={args.launch_key}. Counts only; no secrets/contact values.")

    refused = [n for n in (
        "use_wix_api_key", "call_wix_api", "set_real_domain_connected", "set_public_indexing_enabled",
        "set_page_published", "set_live_form_created", "set_live_webhook_created",
        "set_external_tracking_enabled", "enable_publish", "enable_send",
    ) if getattr(args, n)]
    if refused:
        print(f"Refusing: this script never performs: {', '.join(refused)}. "
              "No Wix API call, no API key use, no live/domain/index/publish/form/webhook/tracking changes.")
        return 1

    confirm_flags = (
        args.confirm_real_domain_not_connected, args.confirm_public_indexing_disabled,
        args.confirm_page_not_published, args.confirm_no_live_form,
        args.confirm_no_live_webhook, args.confirm_no_external_tracking,
    )
    if args.mark_safety_checks_passed and not all(confirm_flags):
        print("Refusing: --mark-safety-checks-passed requires ALL six --confirm-* safety flags "
              "(real-domain-not-connected, public-indexing-disabled, page-not-published, "
              "no-live-form, no-live-webhook, no-external-tracking).")
        return 1

    do_site = args.confirm_staging_site_created_manually and bool(args.staging_site_name or args.staging_site_url)
    if args.confirm_staging_site_created_manually and not do_site:
        print("Note: --confirm-staging-site-created-manually given but no --staging-site-name/--staging-site-url "
              "supplied; NOT fabricating a staging site. Staging status stays 'planned'.")

    any_action = (do_site or args.mark_setup_started or args.mark_gallery_white_shell_started
                  or args.mark_safety_checks_passed or args.record_api_permission_review_deferred)
    if not any_action:
        print("Nothing to do: pass at least one action flag (e.g. --mark-setup-started, "
              "--record-api-permission-review-deferred, or staging site details with confirmation).")
        return 1

    if not project_exists(args.launch_key):
        print(f"Refusing: launch project '{args.launch_key}' not found.")
        return 1

    print("projected actions (counts only):")
    if do_site:
        print(f"  staging site -> created_manually (name recorded: {bool(args.staging_site_name)}, url recorded: {bool(args.staging_site_url)})")
    elif args.confirm_staging_site_created_manually:
        print("  staging site -> unchanged (planned); no site details supplied")
    else:
        print("  staging site -> unchanged (planned)")
    if args.mark_setup_started:
        print("  setup checklist items pending -> in_progress")
    if args.mark_gallery_white_shell_started:
        print("  hero / navigation / content_sections checklist items pending -> in_progress")
    if args.mark_safety_checks_passed:
        print("  safety checklist + absence QA (domain/noindex/webhook/tracking) -> passed (visual/content QA NOT marked)")
    if args.record_api_permission_review_deferred:
        print("  action log: Wix API permission/key usage DEFERRED (no key read/stored, no external_call_allowed change)")
    print("  Wix API calls: 0   Wix API key reads: 0   publishing: 0   live forms/webhooks: 0")
    print("  real domain / public indexing / external tracking: unchanged (off)")
    print("  inbound_leads_created: 0   contacts_created_or_merged: 0   messages_sent: 0")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    if not (args.performed_by or "").strip() or not (args.decision_notes or "").strip():
        print("Refusing: --performed-by and --decision-notes are required for an audited apply.")
        return 1

    code, output = run_psql(apply_sql(args, do_site))
    print("Staging build progress recorded:" if code == 0 else "Record FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
