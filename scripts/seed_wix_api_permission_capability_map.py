#!/usr/bin/env python3
"""Phase 7.21 — seed the Wix API permission / integration capability map. Dry-run by default.

Maps Wix API permissions (as reviewed by the operator in the Wix dashboard) to Real Deal Housing
OS capabilities, defines FUTURE API-key profiles, and queues human review BEFORE any key is created
or used. It stores NO secrets and NO API keys.

It performs NO Wix API call, NEVER requests/reads/stores an API key, NEVER inspects .env for Wix
secrets (it only reads Postgres connection values to talk to the local DB), and never publishes,
sends, or creates leads/contacts. Every key profile carries secret_value_stored=false and
external_call_allowed=false. Writing requires BOTH --real-ok and --apply. Counts only; never prints
secrets.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.21"
SOURCE = "wix_api_permission_capability_map_seed"

# (permission_key, display_name, category, recommended_status, risk_level, useful_for, blocked_reason, safe_summary)
CATALOG = [
    # --- Useful soon / staging ---
    ("manage_site_branches", "Manage Site Branches", "staging", "allow_staging_only", "low",
     ["staging_preview"], None, "Create/manage Wix site branches for isolated staging/preview builds."),
    ("read_site_urls", "Read Site URLs", "staging", "read_only_preferred", "low",
     ["staging_preview"], None, "Read staging/preview site URLs; read-only, no write."),
    ("wix_forms", "Wix Forms", "forms", "allow_staging_only", "medium",
     ["lead_intake"], None, "Read/define Wix Forms structure for the staging lead form."),
    ("manage_form_submissions", "Manage Form Submissions", "forms", "read_only_preferred", "medium",
     ["lead_intake"], None, "Read staging form submissions for later fake-lead ingestion; read-first."),
    ("wix_data", "Wix Data", "cms", "allow_staging_only", "medium",
     ["wix_cms_sync"], None, "Read/write Wix CMS (Data) collections for content sync in staging."),
    ("wix_blog", "Wix Blog", "blog_seo", "allow_staging_only", "medium",
     ["blog_automation"], None, "Manage blog drafts for SEO content; publishing stays draft-only in staging."),
    ("manage_faq", "Manage FAQ", "blog_seo", "allow_staging_only", "low",
     ["blog_automation"], None, "Manage SEO FAQ entries for the staging site."),
    ("manage_site_media", "Manage Site Media", "media", "allow_staging_only", "medium",
     ["media_library"], None, "Upload/organize media assets in the staging media library."),
    ("list_marketing_tags", "List Marketing Tags", "tracking", "read_only_preferred", "low",
     ["tracking_tags"], None, "Inspect installed marketing tags (read-only); no tag writes."),
    # --- Useful later / gated ---
    ("manage_marketing_tags", "Manage Marketing Tags", "tracking", "allow_later", "high",
     ["tracking_tags"], "Tag writes affect tracking; gate behind staging QA + tracking review.",
     "Install/manage GA4/GTM/Meta tags later, after consent + tracking review."),
    ("manage_cookie_consent_banner", "Manage Cookie Consent Banner", "consent", "allow_later", "medium",
     ["consent_management"], "Consent UX is compliance-sensitive; review first.",
     "Configure the cookie consent banner later."),
    ("consent_config", "Consent Config", "consent", "allow_later", "medium",
     ["consent_management"], "Consent configuration; review first.", "Configure consent settings later."),
    ("manage_consent_policy", "Manage Consent Policy", "consent", "allow_later", "high",
     ["consent_management"], "Consent policy is legally sensitive; review first.",
     "Manage consent policy later, with legal/compliance review."),
    ("manage_embedded_scripts", "Manage Embedded Scripts", "scripts", "defer", "high",
     ["tracking_tags"], "Arbitrary script injection is high-risk; defer until strictly needed.",
     "Inject embedded scripts later; high risk, defer."),
    ("custom_embeds", "Custom Embeds", "scripts", "defer", "high",
     ["tracking_tags"], "Custom embeds can run third-party code; defer.", "Custom embeds; defer."),
    ("wix_cli_git_integration", "Wix CLI - Git Integration", "publishing", "allow_later", "medium",
     ["blog_automation"], "Git-to-Wix flow; evaluate later.", "Wix CLI / Git integration for code-based site work later."),
    ("business_info", "Business Info", "cockpit", "allow_later", "low",
     ["cockpit_status"], None, "Read business info for the operator cockpit later."),
    ("wix_analytics", "Wix Analytics", "analytics", "allow_later", "medium",
     ["cockpit_status"], None, "Read Wix Analytics for cockpit reporting later."),
    ("manage_reports", "Manage Reports", "analytics", "allow_later", "medium",
     ["cockpit_status"], None, "Manage analytics reports later."),
    ("wix_inbox", "Wix Inbox", "whatsapp_chat", "allow_later", "medium",
     ["cockpit_status"], "Messaging surface; gate behind consent + messaging review.",
     "Triage Wix Inbox later (no sends until consent/messaging review)."),
    ("wix_chat", "Wix Chat", "whatsapp_chat", "allow_later", "medium",
     ["cockpit_status"], "Chat can send messages; gate behind consent review.",
     "Wix Chat triage later; no automated sends until reviewed."),
    ("manage_email_subscriptions", "Manage Email Subscriptions", "email", "allow_later", "high",
     ["lead_intake"], "Subscriber data + sends are consent-sensitive; defer.",
     "Sync email subscriptions later, after consent review."),
    ("manage_email_marketing", "Manage Email Marketing", "email", "allow_later", "high",
     ["ai_agent_content_ops"], "Email campaign sends require consent + suppression; defer.",
     "Email campaign operations later; sends stay blocked until consent + suppression pass."),
    ("manage_social_posts", "site.scope.SCOPE.DC-PROMOTE.MANAGE-SOCIAL-POSTS", "social", "allow_later", "high",
     ["social_publishing"], "Social posting is outbound publishing; gate behind review.",
     "Manage social posts later; publishing stays gated."),
    ("manage_social_channels", "site.scope.SCOPE.DC-PROMOTE.MANAGE-SOCIAL-CHANNELS", "social", "allow_later", "high",
     ["social_publishing"], "Social channel management; gate behind review.",
     "Manage social channels later; gated."),
    # --- Avoid / defer ---
    ("publish_metasite", "Publish Metasite", "publishing", "avoid", "critical",
     ["production_publish"], "Production publish to the live domain; never select until staging QA + explicit operator approval.",
     "Publishes the site to production — hard-blocked this phase."),
    ("wix_payments", "Wix Payments", "payments", "avoid", "critical",
     [], "Payments out of scope; avoid.", "Payments; not needed, avoid."),
    ("wix_cashier", "Wix Cashier", "payments", "avoid", "critical",
     [], "Payments out of scope; avoid.", "Cashier; avoid."),
    ("wix_pay_links", "Wix Pay Links", "payments", "avoid", "high",
     [], "Payments out of scope; avoid.", "Pay links; avoid."),
    ("wix_invoices", "Wix Invoices", "payments", "avoid", "high",
     [], "Billing out of scope; avoid.", "Invoices; avoid."),
    ("connect_wix_payments_account", "Connect Wix Payments Account", "payments", "avoid", "critical",
     [], "Connecting a payments account is out of scope; avoid.", "Connect payments account; avoid."),
    ("wix_members", "Wix Members", "members", "avoid", "high",
     [], "Member accounts out of scope; avoid.", "Members; avoid."),
    ("manage_members", "Manage Members", "members", "avoid", "high",
     [], "Member management out of scope; avoid.", "Manage members; avoid."),
    ("manage_roles", "Manage Roles", "members", "avoid", "critical",
     [], "Role/permission management is high-risk; avoid.", "Manage roles; avoid."),
    ("server_sign_on_members", "Server Sign On for Members", "members", "avoid", "critical",
     [], "Server-side member auth is high-risk; avoid.", "Server sign-on; avoid."),
    ("wix_secrets", "Wix Secrets", "risky_deferred", "avoid", "critical",
     [], "Secret storage scope is high-risk; avoid (we never store Wix secrets via API).",
     "Wix Secrets scope; avoid."),
    ("invoke_ai_models", "Invoke AI Models", "risky_deferred", "avoid", "high",
     [], "Wix-side AI invocation out of scope; we run our own AI pipeline.", "Invoke AI models; avoid."),
    ("wix_restaurants", "Wix Restaurants", "risky_deferred", "avoid", "low",
     [], "Not relevant to housing; avoid.", "Restaurants; not relevant."),
    ("wix_loyalty", "Wix Loyalty", "risky_deferred", "avoid", "low",
     [], "Not relevant; avoid.", "Loyalty; not relevant."),
    ("wix_donations", "Wix Donations", "risky_deferred", "avoid", "low",
     [], "Not relevant; avoid.", "Donations; not relevant."),
    ("wix_forum", "Wix Forum", "risky_deferred", "avoid", "low",
     [], "Not relevant; avoid.", "Forum; not relevant."),
    ("wix_reviews", "Wix Reviews", "risky_deferred", "avoid", "low",
     [], "Not relevant yet; avoid.", "Reviews; not relevant yet."),
    ("manage_your_app", "Manage Your App", "risky_deferred", "avoid", "high",
     [], "App-management scope is broad/high-risk; avoid.", "Manage your app; avoid."),
    ("manage_notifications", "Manage Notifications", "risky_deferred", "avoid", "medium",
     [], "Notification sends are messaging; avoid until messaging review.", "Notifications; avoid."),
    ("wixel_projects", "Wixel Projects", "risky_deferred", "avoid", "low",
     [], "Not relevant; avoid.", "Wixel projects; not relevant."),
    ("manage_tags_ambiguous", "Manage Tags (ambiguous)", "risky_deferred", "defer", "medium",
     ["tracking_tags"], "Ambiguous 'Manage Tags' scope; do not select until disambiguated.",
     "Ambiguous tag-management scope; defer until clarified."),
]

# (use_case_key, area, status, perm_key, requires_account_id, can_write, can_publish, can_send, summary)
USE_CASES = [
    ("staging_branch_management", "staging_preview", "needs_research", "manage_site_branches", False, True, False, False,
     "Create and manage a staging branch for the Gallery White build."),
    ("staging_preview_url_retrieval", "staging_preview", "needs_research", "read_site_urls", False, False, False, False,
     "Retrieve the staging preview URL (read-only)."),
    ("wix_cms_collection_sync", "wix_cms_sync", "needs_research", "wix_data", False, True, False, False,
     "Sync structured content into Wix CMS collections in staging."),
    ("wix_form_submission_ingestion", "lead_intake", "needs_research", "manage_form_submissions", False, False, False, False,
     "Ingest staging form submissions for the fake-lead test (read-first)."),
    ("wix_blog_draft_publishing_later", "blog_automation", "deferred", "wix_blog", False, True, False, False,
     "Create blog drafts later; publishing stays draft-only until review."),
    ("seo_faq_management", "blog_automation", "needs_research", "manage_faq", False, True, False, False,
     "Manage SEO FAQ entries on the staging site."),
    ("media_upload_organization", "media_library", "needs_research", "manage_site_media", False, True, False, False,
     "Upload and organize media in the staging media library."),
    ("marketing_tag_inspection", "tracking_tags", "needs_research", "list_marketing_tags", False, False, False, False,
     "Inspect installed marketing tags (read-only)."),
    ("ga4_gtm_meta_tag_management_later", "tracking_tags", "deferred", "manage_marketing_tags", False, True, False, False,
     "Manage GA4/GTM/Meta tags later, after tracking + consent review."),
    ("cookie_consent_configuration_later", "consent_management", "deferred", "manage_cookie_consent_banner", False, True, False, False,
     "Configure cookie/consent banner later."),
    ("embedded_script_injection_later", "tracking_tags", "blocked", "manage_embedded_scripts", False, True, False, False,
     "Inject embedded scripts later; high-risk, blocked for now."),
    ("email_subscription_sync_later", "lead_intake", "deferred", "manage_email_subscriptions", False, True, False, False,
     "Sync email subscriptions later, after consent review (no sends)."),
    ("email_campaign_operations_later", "ai_agent_content_ops", "deferred", "manage_email_marketing", False, True, False, False,
     "Email campaign operations later; sends blocked until consent + suppression."),
    ("wix_inbox_chat_triage_later", "cockpit_status", "deferred", "wix_inbox", False, True, False, False,
     "Triage Wix Inbox/Chat later; no automated sends until messaging review."),
    ("social_post_channel_ops_later", "social_publishing", "deferred", "manage_social_posts", True, True, False, False,
     "Manage social posts/channels later; publishing stays gated."),
    ("production_publish_later_blocked", "production_publish", "blocked", "publish_metasite", True, True, True, False,
     "Production publish to the live domain — blocked until staging QA + operator approval."),
]

# (profile_key, environment, purpose, allowed[], forbidden[], secret_location, summary)
KEY_PROFILES = [
    ("wix_staging_discovery_key", "staging",
     "Read-first staging discovery: read URLs/branches and inspect CMS/forms/blog/FAQ/media/tags.",
     ["read_site_urls", "manage_site_branches", "wix_data", "wix_forms", "wix_blog", "manage_faq",
      "manage_site_media", "list_marketing_tags"],
     ["publish_metasite", "wix_payments", "wix_members", "wix_secrets", "manage_email_marketing",
      "manage_embedded_scripts", "manage_marketing_tags"],
     "not_created",
     "Planned staging discovery key. Read-first; never publishes, never sends, never touches payments/members/secrets."),
    ("wix_staging_build_key_later", "staging",
     "Staging build write access for the Gallery White build (CMS/blog/FAQ/media/forms/branches).",
     ["wix_data", "wix_blog", "manage_faq", "manage_site_media", "wix_forms", "manage_site_branches"],
     ["publish_metasite", "wix_payments", "wix_members", "wix_secrets", "manage_email_marketing"],
     "not_created",
     "Planned staging build key (later). Writes to staging only; no production publish, payments, members, or secrets."),
    ("wix_tracking_key_later", "staging",
     "Tracking/consent setup in staging first: marketing tags + cookie/consent config.",
     ["list_marketing_tags", "manage_marketing_tags", "manage_cookie_consent_banner", "consent_config",
      "manage_consent_policy"],
     ["publish_metasite", "wix_forms", "manage_email_marketing", "wix_payments", "wix_members", "wix_secrets"],
     "not_created",
     "Planned tracking key (later). Staging first; no form writes, no sends, no payments/members/secrets."),
    ("wix_production_key_future", "production",
     "Future production key — blocked until staging fake-lead test passes and the operator approves.",
     [],
     ["publish_metasite", "wix_payments", "wix_cashier", "wix_members", "manage_roles", "wix_secrets",
      "manage_email_marketing"],
     "not_created",
     "Planned production key (future). Forbidden by default; blocked until staging QA + fake-lead test + operator approval."),
]

# (review_type, priority, perm_key|None, profile_key|None, use_case_key|None)
REVIEWS = [
    ("permission_review", "high", None, None, None),
    ("risk_review", "blocker", "wix_payments", None, None),
    ("staging_only_review", "normal", "manage_site_branches", None, None),
    ("production_blocker_review", "blocker", "publish_metasite", None, "production_publish_later_blocked"),
    ("publish_permission_review", "blocker", "publish_metasite", None, None),
    ("secret_storage_review", "blocker", "wix_secrets", None, None),
    ("key_profile_review", "high", None, "wix_staging_discovery_key", None),
    ("key_profile_review", "normal", None, "wix_staging_build_key_later", None),
    ("key_profile_review", "normal", None, "wix_tracking_key_later", None),
    ("key_profile_review", "blocker", None, "wix_production_key_future", None),
]


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
    if isinstance(value, bool):
        return "true" if value else "false"
    return "'" + str(value).replace("'", "''") + "'"


def json_literal(value) -> str:
    return "'" + json.dumps(value).replace("'", "''") + "'::jsonb"


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


def existing_count() -> int:
    code, output = run_psql(
        f"SELECT count(*) FROM wix_api_permission_catalog WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}';"
    )
    if code != 0:
        return -1
    try:
        return int(output.strip())
    except ValueError:
        return -1


def ctx(extra: dict | None = None) -> str:
    pairs = [
        "'phase'", f"'{PHASE}'",
        "'source'", f"'{SOURCE}'",
        "'external_calls_made'", "false",
        "'api_key_requested'", "false",
        "'secret_value_stored'", "false",
        "'publish_enabled'", "false",
        "'communication_sent'", "false",
    ]
    if extra:
        for k, v in extra.items():
            pairs.append(sql_literal(k))
            pairs.append(sql_literal(v))
    return "jsonb_build_object(" + ", ".join(pairs) + ")"


def cat_ref(perm_key) -> str:
    if perm_key is None:
        return "NULL"
    return (f"(SELECT id FROM wix_api_permission_catalog WHERE permission_key = {sql_literal(perm_key)} "
            f"AND raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' LIMIT 1)")


def profile_ref(profile_key) -> str:
    if profile_key is None:
        return "NULL"
    return (f"(SELECT id FROM wix_api_key_profiles WHERE profile_key = {sql_literal(profile_key)} "
            f"AND raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' LIMIT 1)")


def usecase_ref(use_case_key) -> str:
    if use_case_key is None:
        return "NULL"
    return (f"(SELECT id FROM wix_api_integration_use_cases WHERE use_case_key = {sql_literal(use_case_key)} "
            f"AND raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}' LIMIT 1)")


def apply_sql() -> str:
    blocks = ["BEGIN;"]

    # Idempotent reset (FK order: review items -> use cases -> key profiles -> catalog)
    for tbl in ("wix_api_permission_review_items", "wix_api_integration_use_cases",
                "wix_api_key_profiles", "wix_api_permission_catalog"):
        blocks.append(
            f"DELETE FROM {tbl} WHERE raw_context->>'phase' = '{PHASE}' AND raw_context->>'source' = '{SOURCE}';"
        )

    # Catalog
    for pk, dn, cat, rec, risk, useful, blocked, summary in CATALOG:
        blocks.append(
            "INSERT INTO wix_api_permission_catalog "
            "(permission_key, permission_display_name, permission_category, recommended_status, risk_level, "
            "useful_for, blocked_reason, safe_summary, official_doc_url, raw_context) VALUES ("
            f"{sql_literal(pk)}, {sql_literal(dn)}, {sql_literal(cat)}, {sql_literal(rec)}, {sql_literal(risk)}, "
            f"{json_literal(useful)}, {sql_literal(blocked)}, {sql_literal(summary)}, "
            f"{sql_literal('https://dev.wix.com/docs')}, {ctx()});"
        )

    # Use cases
    for uk, area, status, perm, acct, can_write, can_pub, can_send, summary in USE_CASES:
        blocks.append(
            "INSERT INTO wix_api_integration_use_cases "
            "(permission_catalog_id, use_case_key, use_case_area, use_case_status, requires_api_key, requires_site_id, "
            "requires_account_id, can_run_read_only, can_write, can_publish, can_send_messages, safe_summary, raw_context) VALUES ("
            f"{cat_ref(perm)}, {sql_literal(uk)}, {sql_literal(area)}, {sql_literal(status)}, true, true, "
            f"{sql_literal(acct)}, true, {sql_literal(can_write)}, {sql_literal(can_pub)}, {sql_literal(can_send)}, "
            f"{sql_literal(summary)}, {ctx()});"
        )

    # Key profiles
    for prof, env, purpose, allowed, forbidden, secloc, summary in KEY_PROFILES:
        blocks.append(
            "INSERT INTO wix_api_key_profiles "
            "(profile_key, profile_status, environment, purpose, allowed_permission_keys, forbidden_permission_keys, "
            "secret_value_stored, secret_location, external_call_allowed, safe_summary, raw_context) VALUES ("
            f"{sql_literal(prof)}, 'planned', {sql_literal(env)}, {sql_literal(purpose)}, "
            f"{json_literal(allowed)}, {json_literal(forbidden)}, false, {sql_literal(secloc)}, false, "
            f"{sql_literal(summary)}, {ctx()});"
        )

    # Review items
    for rt, pri, perm, prof, uc in REVIEWS:
        blocks.append(
            "INSERT INTO wix_api_permission_review_items "
            "(permission_catalog_id, key_profile_id, use_case_id, review_type, status, priority, raw_context) VALUES ("
            f"{cat_ref(perm)}, {profile_ref(prof)}, {usecase_ref(uc)}, {sql_literal(rt)}, 'pending', {sql_literal(pri)}, {ctx()});"
        )

    # Hard guard
    blocks.append(f"""
DO $GUARD$
DECLARE active int; ext int; sec int; pubperm int; sendperm int; inbound int; contacts_count int;
BEGIN
  SELECT count(*) INTO active FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}' AND profile_status = 'active';
  SELECT count(*) INTO ext FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}' AND external_call_allowed;
  SELECT count(*) INTO sec FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}' AND secret_value_stored;
  SELECT publish_permission_allowed_count INTO pubperm FROM vw_dlf_wix_api_readiness;
  SELECT send_permission_allowed_count INTO sendperm FROM vw_dlf_wix_api_readiness;
  SELECT count(*) INTO inbound FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  IF active > 0 THEN RAISE EXCEPTION 'Refusing: a key profile is active.'; END IF;
  IF ext > 0 THEN RAISE EXCEPTION 'Refusing: a key profile has external_call_allowed.'; END IF;
  IF sec > 0 THEN RAISE EXCEPTION 'Refusing: a key profile reports secret_value_stored.'; END IF;
  IF pubperm > 0 THEN RAISE EXCEPTION 'Refusing: publish permission marked allowed (%).', pubperm; END IF;
  IF sendperm > 0 THEN RAISE EXCEPTION 'Refusing: send permission marked allowed (%).', sendperm; END IF;
  IF inbound <> 0 THEN RAISE EXCEPTION 'Refusing: inbound lead count changed to %.', inbound; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
END $GUARD$;
COMMIT;

SELECT 'permission_catalog', count(*)::text FROM wix_api_permission_catalog WHERE raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'use_cases', count(*)::text FROM wix_api_integration_use_cases WHERE raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'key_profiles', count(*)::text FROM wix_api_key_profiles WHERE raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'review_items', count(*)::text FROM wix_api_permission_review_items WHERE raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'allowed_now_count', allowed_now_count::text FROM vw_dlf_wix_api_readiness
UNION ALL SELECT 'allow_staging_only_count', allow_staging_only_count::text FROM vw_dlf_wix_api_readiness
UNION ALL SELECT 'deferred_count', deferred_count::text FROM vw_dlf_wix_api_readiness
UNION ALL SELECT 'avoid_count', avoid_count::text FROM vw_dlf_wix_api_readiness
UNION ALL SELECT 'active_key_profiles', active_key_profiles::text FROM vw_dlf_wix_api_readiness
UNION ALL SELECT 'external_call_allowed_count', external_call_allowed_count::text FROM vw_dlf_wix_api_readiness
UNION ALL SELECT 'publish_permission_allowed_count', publish_permission_allowed_count::text FROM vw_dlf_wix_api_readiness
UNION ALL SELECT 'send_permission_allowed_count', send_permission_allowed_count::text FROM vw_dlf_wix_api_readiness
UNION ALL SELECT 'ready_for_api_key_creation', ready_for_api_key_creation::text FROM vw_dlf_wix_api_readiness
UNION ALL SELECT 'ready_for_api_call_test', ready_for_api_call_test::text FROM vw_dlf_wix_api_readiness
ORDER BY 1;
""")
    return "\n".join(blocks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the Wix API permission/capability map. Dry-run by default.")
    parser.add_argument("--allow-existing", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print("Wix API permission/capability map seed. Counts only; no secrets, no API keys, no Wix API calls.")

    existing = existing_count()
    if existing < 0:
        print("Refusing: could not probe existing catalog rows.")
        return 1
    if existing > 0 and not args.allow_existing:
        print(f"Refusing: {existing} Phase 7.21 catalog row(s) already exist. Re-run with --allow-existing to replace.")
        return 1

    n_staging = sum(1 for c in CATALOG if c[3] in ("allow_staging_only", "read_only_preferred"))
    n_later = sum(1 for c in CATALOG if c[3] in ("allow_later", "defer"))
    n_avoid = sum(1 for c in CATALOG if c[3] == "avoid")
    print("projected:")
    print(f"  permission catalog rows: {len(CATALOG)}  (staging/read: {n_staging}, later/defer: {n_later}, avoid: {n_avoid})")
    print(f"  integration use cases: {len(USE_CASES)}")
    print(f"  key profiles: {len(KEY_PROFILES)}  (all planned, secret_value_stored=false, external_call_allowed=false)")
    print(f"  review items: {len(REVIEWS)}  (all pending)")
    print("  Wix API calls: 0   API keys requested/read/stored: 0   secrets stored: 0")
    print("  publishing: 0   live forms/webhooks: 0   sends: 0   leads/contacts changed: 0")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql())
    print("Capability map seeded:" if code == 0 else "Seed FAILED (rolled back):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
