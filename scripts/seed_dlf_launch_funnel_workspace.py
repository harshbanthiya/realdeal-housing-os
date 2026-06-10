#!/usr/bin/env python3
"""Phase 7.1: seed the DLF launch funnel & campaign DRAFT workspace (no sends/publishing).

Seeds, for an existing launch_projects row, a full funnel scaffold: 1 landing-page spec,
1 lead-capture form spec, UTM specs per channel, 10 content pillars, WhatsApp/email/phone/
referral DRAFT message templates, >=15 social DRAFT content ideas, lead-scoring rules, a human
review item per draft, and any missing readiness checks.

Everything is review-gated and inert: send_enabled=false, publish_enabled=false,
human_review_required=true. Draft copy uses ONLY compliant placeholders — no false scarcity, no
guaranteed returns, no unverified RERA, no exact price/area — with markers [PROJECT_NAME_CONFIRM],
[RERA_VERIFY], [PRICE_VERIFY], [BROCHURE_LINK_PENDING], [WIX_PAGE_PENDING], [VERIFY], and
opt-out/consent placeholders. No sending, no publishing, no external API, no scrape, no contact
import/select/create/merge, no personal data.

All rows tagged raw_context: phase='7.1', source='dlf_launch_funnel_workspace_seed',
send_enabled=false, publish_enabled=false, communication_sent=false, external_calls_made=false.
Dry-run by default; --real-ok required; --apply to write. Prints counts only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.1"
SOURCE = "dlf_launch_funnel_workspace_seed"
BASE_TAG = {
    "phase": PHASE, "source": SOURCE,
    "send_enabled": False, "publish_enabled": False,
    "communication_sent": False, "external_calls_made": False,
}

# Tables that hold this phase's tagged rows (for the existence/refuse check).
PHASE_TABLES = [
    "launch_landing_page_specs", "launch_lead_capture_forms", "launch_utm_campaign_specs",
    "launch_content_pillars", "launch_message_templates", "launch_social_content_drafts",
    "launch_lead_scoring_rules", "launch_draft_review_items",
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
    return "'" + str(value).replace("'", "''") + "'"


def num(value) -> str:
    return "NULL" if value is None else str(value)


def jsonb_lit(obj) -> str:
    return sql_literal(json.dumps(obj)) + "::jsonb"


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
    return result.returncode, (result.stdout.strip() or result.stderr.strip())


def tag(extra: dict | None = None) -> str:
    obj = dict(BASE_TAG)
    if extra:
        obj.update(extra)
    return jsonb_lit(obj)


# ----------------------------------------------------------------- content data

UTM_SPECS = [
    ("seo", "dlf-westend-seo-launch", "google", "organic", "andheri_west_launch", "awareness"),
    ("blog", "dlf-westend-blog", "blog", "content", "project_overview", "consideration"),
    ("instagram", "dlf-westend-ig", "instagram", "social", "teaser", "awareness"),
    ("youtube_shorts", "dlf-westend-yt", "youtube", "social", "walkthrough", "consideration"),
    ("whatsapp", "dlf-westend-wa", "whatsapp", "messaging", "interest_capture", "conversion"),
    ("email", "dlf-westend-email", "email", "email", "preview", "nurture"),
    ("referral", "dlf-westend-referral", "referral", "referral", "owner_network", "referral"),
    ("listing_portal", "dlf-westend-portal", "listing_portal", "referral", "portal_listing", "awareness"),
]

CONTENT_PILLARS = [
    ("dlf_brand_return_to_mumbai", "DLF brand — return to Mumbai", "high_budget_buyers", "awareness",
     "Highlight DLF entering/returning to the Mumbai market [VERIFY].", "DLF credentials [RERA_VERIFY]"),
    ("andheri_west_luxury_location", "Andheri West premium location", "andheri_west_buyers", "awareness",
     "Andheri West location advantages.", "Connectivity/landmark facts [VERIFY]"),
    ("limited_launch_window", "Launch window (no false scarcity)", "high_budget_buyers", "consideration",
     "Early-access launch interest — no false scarcity.", "Launch timeline [VERIFY]"),
    ("investor_entry_angle", "Investor entry angle", "investor_buyers", "consideration",
     "Appreciation/rental potential — no guaranteed returns.", "Market data [VERIFY]"),
    ("nri_mumbai_base", "NRI Mumbai base", "nri_buyers", "consideration",
     "NRI-friendly buying basics.", "Process/compliance facts [VERIFY]"),
    ("family_upgrade_3_4_bhk", "Family upgrade 3/4 BHK", "high_budget_buyers", "consideration",
     "Spacious 3/4 BHK homes.", "Floor plans [PRICE_VERIFY]"),
    ("similar_owner_referral", "Owner-network referral", "owner_network_referrals", "referral",
     "Refer friends/family in your network.", "Referral program [VERIFY]"),
    ("rera_verified_project_facts", "RERA-verified facts only", "all", "consideration",
     "Share verified project facts only [RERA_VERIFY].", "RERA registration [RERA_VERIFY]"),
    ("site_visit_brochure_angle", "Site visit & brochure", "high_budget_buyers", "conversion",
     "Book a site visit / request brochure.", "Brochure [BROCHURE_LINK_PENDING]"),
    ("price_sheet_waitlist", "Price sheet waitlist", "high_budget_buyers", "conversion",
     "Join the waitlist for the price sheet.", "Price [PRICE_VERIFY]"),
]

OPTOUT = "Reply STOP to opt out."
# (channel, template_key, template_type, segment, funnel_stage, subject, body, cta, review_type)
MESSAGE_TEMPLATES = [
    ("whatsapp", "wa_pre_launch_interest", "pre_launch_interest", "high_budget_buyers", "awareness",
     None, "Early heads-up on a new DLF launch in Andheri West ([PROJECT_NAME_CONFIRM]). Want details? " + OPTOUT,
     "Reply YES for details", "whatsapp_copy_review"),
    ("whatsapp", "wa_brochure_request", "brochure_request", "high_budget_buyers", "consideration",
     None, "Brochure for [PROJECT_NAME_CONFIRM] [BROCHURE_LINK_PENDING]. Details [RERA_VERIFY]/[PRICE_VERIFY]. " + OPTOUT,
     "Request brochure", "whatsapp_copy_review"),
    ("whatsapp", "wa_site_visit_interest", "site_visit_interest", "high_budget_buyers", "conversion",
     None, "Book a site visit for [PROJECT_NAME_CONFIRM]? Share a preferred day. " + OPTOUT,
     "Book site visit", "whatsapp_copy_review"),
    ("whatsapp", "wa_investor_angle", "investor_angle", "investor_buyers", "consideration",
     None, "Investor preview for [PROJECT_NAME_CONFIRM], Andheri West. Verified facts only [RERA_VERIFY]; no guaranteed returns. " + OPTOUT,
     "Get investor note", "whatsapp_copy_review"),
    ("whatsapp", "wa_nri_angle", "nri_angle", "nri_buyers", "consideration",
     None, "NRI-friendly buying for [PROJECT_NAME_CONFIRM]. Happy to share the process. " + OPTOUT,
     "Learn more", "whatsapp_copy_review"),
    ("whatsapp", "wa_owner_referral", "follow_up", "owner_network_referrals", "referral",
     None, "We are helping buyers explore [PROJECT_NAME_CONFIRM]. Know someone interested? " + OPTOUT,
     "Refer someone", "whatsapp_copy_review"),
    ("whatsapp", "wa_launch_day", "launch_day", "high_budget_buyers", "conversion",
     None, "[PROJECT_NAME_CONFIRM] launch updates are live. Want details/brochure? " + OPTOUT,
     "Get launch details", "whatsapp_copy_review"),
    ("email", "em_pre_launch_intro", "pre_launch_interest", "high_budget_buyers", "awareness",
     "An early look: new DLF launch in Andheri West",
     "Sharing an early look at [PROJECT_NAME_CONFIRM] in Andheri West [RERA_VERIFY]. Unsubscribe link [pending].",
     "Register interest", "email_copy_review"),
    ("email", "em_detailed_project_note", "pre_launch_interest", "high_budget_buyers", "consideration",
     "[PROJECT_NAME_CONFIRM]: project details",
     "Project details for [PROJECT_NAME_CONFIRM]. Pricing [PRICE_VERIFY]; brochure [BROCHURE_LINK_PENDING]. Unsubscribe link [pending].",
     "Request brochure", "email_copy_review"),
    ("email", "em_launch_reminder", "launch_day", "high_budget_buyers", "conversion",
     "Launch update: [PROJECT_NAME_CONFIRM]",
     "Launch update for [PROJECT_NAME_CONFIRM] [WIX_PAGE_PENDING]. Verified facts only [RERA_VERIFY]. Unsubscribe link [pending].",
     "See details", "email_copy_review"),
    ("email", "em_referral_request", "follow_up", "owner_network_referrals", "referral",
     "Know someone looking in Andheri West?",
     "If you know someone exploring Andheri West, share [PROJECT_NAME_CONFIRM] with them. Unsubscribe link [pending].",
     "Refer a friend", "email_copy_review"),
    ("phone_call", "ph_intro_script", "pre_launch_interest", "high_budget_buyers", "awareness",
     None, "Call script: introduce [PROJECT_NAME_CONFIRM], confirm interest, offer brochure [BROCHURE_LINK_PENDING], honour DND/consent.",
     "Offer brochure", "compliance_review"),
    ("referral", "ref_ask_script", "follow_up", "owner_network_referrals", "referral",
     None, "Referral-ask script for the owner network; never share personal data without consent.",
     "Ask for referral", "compliance_review"),
]

# 15 social drafts: (platform, content_key, content_type, segment, funnel_stage, hook, cta)
SOCIAL_DRAFTS = [
    ("instagram_reel", "ig_teaser_01", "teaser", "high_budget_buyers", "awareness", "New DLF launch in Andheri West? [PROJECT_NAME_CONFIRM]", "Register interest"),
    ("instagram_reel", "ig_location_01", "location_angle", "andheri_west_buyers", "awareness", "Why Andheri West?", "Learn more"),
    ("instagram_reel", "ig_educational_01", "educational", "high_budget_buyers", "consideration", "What makes a launch worth it", "Get the facts"),
    ("instagram_reel", "ig_investment_01", "investment_angle", "investor_buyers", "consideration", "Investor lens (no guaranteed returns)", "Get investor note"),
    ("instagram_reel", "ig_family_01", "educational", "high_budget_buyers", "consideration", "3/4 BHK family upgrade", "See plans [PRICE_VERIFY]"),
    ("instagram_story", "ig_story_countdown_01", "countdown", "high_budget_buyers", "conversion", "Launch coming soon [VERIFY]", "Join waitlist"),
    ("instagram_story", "ig_story_faq_01", "faq", "high_budget_buyers", "consideration", "Your launch questions", "Ask us"),
    ("instagram_story", "ig_story_update_01", "launch_update", "high_budget_buyers", "awareness", "Launch update [WIX_PAGE_PENDING]", "See details"),
    ("youtube_short", "yt_walkthrough_01", "educational", "high_budget_buyers", "consideration", "Andheri West micro-market", "Watch more"),
    ("youtube_short", "yt_teaser_01", "teaser", "high_budget_buyers", "awareness", "A new DLF address [PROJECT_NAME_CONFIRM]", "Register interest"),
    ("youtube_short", "yt_investor_01", "investment_angle", "investor_buyers", "consideration", "Should investors look here?", "Get investor note"),
    ("instagram_reel", "ig_nri_01", "educational", "nri_buyers", "consideration", "Buying from abroad", "Learn the process"),
    ("instagram_reel", "ig_referral_01", "referral", "owner_network_referrals", "referral", "Refer and help a friend", "Refer someone"),
    ("instagram_reel", "ig_sitevisit_01", "launch_update", "high_budget_buyers", "conversion", "Book a site visit", "Book now"),
    ("instagram_story", "ig_story_brochure_01", "launch_update", "high_budget_buyers", "conversion", "Brochure ready soon [BROCHURE_LINK_PENDING]", "Request brochure"),
]

# (rule_key, signal_type, score_delta, priority_label, safe_summary)
SCORING_RULES = [
    ("budget_fit", "budget", 30, "hot", "Budget matches launch ticket band."),
    ("config_3_4_bhk_interest", "configuration_interest", 20, "warm", "Interested in 3/4 BHK."),
    ("site_visit_requested", "site_visit_request", 40, "urgent", "Requested a site visit."),
    ("brochure_requested", "brochure_request", 15, "warm", "Requested the brochure."),
    ("andheri_west_interest", "location_interest", 15, "warm", "Interested in Andheri West."),
    ("nri_buyer", "nri", 10, "warm", "NRI buyer profile."),
    ("investor_buyer", "investor", 10, "warm", "Investor profile."),
    ("owner_referral", "owner_referral", 25, "hot", "Arrived via owner referral."),
    ("fast_timeline", "timeframe", 25, "hot", "Short purchase timeline."),
    ("repeat_engagement", "returning_lead", 20, "warm", "Repeat/returning engagement."),
]

# Readiness checks this phase ensures exist (only inserted if missing). (check_type, severity)
EXTRA_CHECKS = [
    ("lead_scoring_reviewed", "normal"),
    ("utm_tracking_ready", "normal"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed the DLF launch funnel workspace (review-gated).")
    ap.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-existing", action="store_true")
    args = ap.parse_args()

    if not args.real_ok:
        print("Refusing: --real-ok is required (even for the dry-run plan).")
        return 1

    code, out = run_psql(
        f"SELECT id FROM launch_projects WHERE launch_key = {sql_literal(args.launch_key)};")
    if code != 0 or not out:
        print(f"Refusing: launch project not found for launch_key={args.launch_key!r}. Run Phase 7.0 seed first.")
        return 1
    pid = out.splitlines()[0]

    existing = 0
    for t in PHASE_TABLES:
        c, o = run_psql(f"SELECT count(*) FROM {t} WHERE raw_context->>'phase' = '{PHASE}' "
                        f"AND raw_context->>'source' = '{SOURCE}';")
        existing += int(o) if (c == 0 and o.isdigit()) else 0
    if existing and not args.allow_existing:
        print(f"Refusing: {existing} Phase 7.1 row(s) already exist. Use --allow-existing to add more.")
        return 1

    # Planned counts.
    plan = {
        "landing_page_specs": 1, "lead_capture_forms": 1, "utm_campaign_specs": len(UTM_SPECS),
        "content_pillars": len(CONTENT_PILLARS), "message_templates": len(MESSAGE_TEMPLATES),
        "social_content_drafts": len(SOCIAL_DRAFTS), "lead_scoring_rules": len(SCORING_RULES),
    }
    # review items: one per draft + 2 launch-level (project_name_review, consent_review)
    n_reviews = sum(plan.values()) + 2

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== Phase 7.1 DLF launch funnel workspace seed [{mode}] ===")
    print(f"launch_key={args.launch_key}")
    for k, v in plan.items():
        print(f"  {k}={v}")
    print(f"  draft_review_items={n_reviews}")
    print(f"  extra_readiness_checks(if missing)={len(EXTRA_CHECKS)}")
    print("send_enabled=0  publish_enabled=0  human_review_required=all  communication_sent=0  "
          "contacts_selected=0  external_calls=0")

    if not args.apply:
        print("DRY-RUN only: no DB writes. Re-run with --apply to seed.")
        return 0

    sql = ["BEGIN;"]
    reviews: list[tuple[str, str | None, str | None, str]] = []  # (review_type, fk_col, draft_id, priority)

    # 1. landing page spec
    lp_id = str(uuid.uuid4())
    sections = ["hero", "highlights", "location_andheri_west", "floor_plans_PRICE_VERIFY",
                "rera_disclaimer_RERA_VERIFY", "lead_form", "faq"]
    disclaimers = ["RERA registration to be verified [RERA_VERIFY]",
                   "Prices/areas indicative, subject to confirmation [PRICE_VERIFY]",
                   "Project name pending confirmation [PROJECT_NAME_CONFIRM]"]
    sql.append(
        "INSERT INTO launch_landing_page_specs (id, launch_project_id, page_key, page_title, page_slug, "
        "page_status, hero_headline, hero_subheadline, primary_cta, secondary_cta, form_goal, "
        "required_sections, trust_disclaimers, rera_disclaimer_required, project_name_confirmation_required, "
        "human_review_required, publish_enabled, raw_context) VALUES ("
        f"{sql_literal(lp_id)}, {sql_literal(pid)}, 'dlf-westend-launch-lp', "
        "'[PROJECT_NAME_CONFIRM] — Andheri West Launch', 'dlf-westend-andheri-west', 'draft', "
        "'[PROJECT_NAME_CONFIRM] — A new DLF launch in Andheri West [RERA_VERIFY]', "
        "'Register your interest for early access. Pricing [PRICE_VERIFY]. Brochure [BROCHURE_LINK_PENDING].', "
        "'Request brochure', 'Book a site visit', 'brochure_request', "
        f"{jsonb_lit(sections)}, {jsonb_lit(disclaimers)}, true, true, true, false, {tag()});")
    reviews.append(("landing_page_review", "landing_page_spec_id", lp_id, "high"))

    # 2. lead capture form spec
    form_id = str(uuid.uuid4())
    req_fields = ["name", "phone", "email", "preferred_configuration"]
    qual_qs = ["budget_range", "preferred_configuration_2_3_4_bhk", "purchase_timeline",
               "buyer_or_investor", "preferred_locality_andheri_west"]
    consent_fields = ["whatsapp_optin", "email_optin", "privacy_consent"]
    sql.append(
        "INSERT INTO launch_lead_capture_forms (id, launch_project_id, form_key, form_status, form_goal, "
        "required_fields, qualification_questions, consent_fields, utm_capture_required, "
        "whatsapp_optin_required, email_optin_required, human_review_required, publish_enabled, raw_context) "
        f"VALUES ({sql_literal(form_id)}, {sql_literal(pid)}, 'dlf-westend-lead-form', 'draft', "
        f"'brochure_request', {jsonb_lit(req_fields)}, {jsonb_lit(qual_qs)}, {jsonb_lit(consent_fields)}, "
        f"true, true, true, true, false, {tag()});")
    reviews.append(("lead_form_review", "lead_capture_form_id", form_id, "high"))

    # 3. UTM specs
    for ch, cname, src, med, angle, stage in UTM_SPECS:
        uid = str(uuid.uuid4())
        sql.append(
            "INSERT INTO launch_utm_campaign_specs (id, launch_project_id, channel, campaign_name, source, "
            "medium, content_angle, funnel_stage, status, raw_context) VALUES ("
            f"{sql_literal(uid)}, {sql_literal(pid)}, {sql_literal(ch)}, {sql_literal(cname)}, "
            f"{sql_literal(src)}, {sql_literal(med)}, {sql_literal(angle)}, {sql_literal(stage)}, 'draft', {tag()});")
        reviews.append(("utm_review", "utm_campaign_spec_id", uid, "normal"))

    # 4. content pillars
    for pk, pn, seg, stage, msg, proof in CONTENT_PILLARS:
        cid = str(uuid.uuid4())
        sql.append(
            "INSERT INTO launch_content_pillars (id, launch_project_id, pillar_key, pillar_name, "
            "audience_segment, funnel_stage, core_message, proof_needed, draft_status, human_review_required, "
            "raw_context) VALUES ("
            f"{sql_literal(cid)}, {sql_literal(pid)}, {sql_literal(pk)}, {sql_literal(pn)}, {sql_literal(seg)}, "
            f"{sql_literal(stage)}, {sql_literal(msg)}, {sql_literal(proof)}, 'draft', true, {tag()});")
        reviews.append(("content_pillar_review", "content_pillar_id", cid, "normal"))

    # 5. message templates
    for ch, tkey, ttype, seg, stage, subj, body, cta, rtype in MESSAGE_TEMPLATES:
        mid = str(uuid.uuid4())
        sql.append(
            "INSERT INTO launch_message_templates (id, launch_project_id, channel, template_key, template_type, "
            "target_segment_key, funnel_stage, template_status, subject, body, cta, consent_required, "
            "suppression_check_required, human_review_required, send_enabled, raw_context) VALUES ("
            f"{sql_literal(mid)}, {sql_literal(pid)}, {sql_literal(ch)}, {sql_literal(tkey)}, {sql_literal(ttype)}, "
            f"{sql_literal(seg)}, {sql_literal(stage)}, 'draft', {sql_literal(subj)}, {sql_literal(body)}, "
            f"{sql_literal(cta)}, true, true, true, false, {tag()});")
        reviews.append((rtype, "message_template_id", mid, "high" if ch in ("whatsapp", "email") else "normal"))

    # 6. social drafts
    for plat, ckey, ctype, seg, stage, hook, cta in SOCIAL_DRAFTS:
        sid = str(uuid.uuid4())
        caption = f"{hook} — verified facts only [RERA_VERIFY]. [PROJECT_NAME_CONFIRM]."
        sql.append(
            "INSERT INTO launch_social_content_drafts (id, launch_project_id, platform, content_key, "
            "content_type, target_segment_key, funnel_stage, draft_status, hook, caption, visual_direction, "
            "cta, hashtags, publish_enabled, human_review_required, raw_context) VALUES ("
            f"{sql_literal(sid)}, {sql_literal(pid)}, {sql_literal(plat)}, {sql_literal(ckey)}, {sql_literal(ctype)}, "
            f"{sql_literal(seg)}, {sql_literal(stage)}, 'draft', {sql_literal(hook)}, {sql_literal(caption)}, "
            "'[VISUAL_DIRECTION_PENDING]', "
            f"{sql_literal(cta)}, '#AndheriWest #DLF [VERIFY]', false, true, {tag()});")
        reviews.append(("social_copy_review", "social_content_draft_id", sid, "normal"))

    # 7. lead scoring rules
    for rk, sig, delta, label, summary in SCORING_RULES:
        rid = str(uuid.uuid4())
        sql.append(
            "INSERT INTO launch_lead_scoring_rules (id, launch_project_id, rule_key, rule_status, signal_type, "
            "score_delta, priority_label, safe_summary, human_review_required, raw_context) VALUES ("
            f"{sql_literal(rid)}, {sql_literal(pid)}, {sql_literal(rk)}, 'draft', {sql_literal(sig)}, "
            f"{num(delta)}, {sql_literal(label)}, {sql_literal(summary)}, true, {tag()});")
        reviews.append(("lead_scoring_review", "lead_scoring_rule_id", rid, "normal"))

    # 8. launch-level reviews (no draft FK)
    reviews.append(("project_name_review", None, None, "high"))
    reviews.append(("consent_review", None, None, "high"))

    # review items
    for rtype, fk_col, draft_id, priority in reviews:
        if fk_col and draft_id:
            sql.append(
                f"INSERT INTO launch_draft_review_items (launch_project_id, {fk_col}, review_type, status, "
                f"priority, raw_context) VALUES ({sql_literal(pid)}, {sql_literal(draft_id)}, "
                f"{sql_literal(rtype)}, 'pending', {sql_literal(priority)}, {tag()});")
        else:
            sql.append(
                "INSERT INTO launch_draft_review_items (launch_project_id, review_type, status, priority, "
                f"raw_context) VALUES ({sql_literal(pid)}, {sql_literal(rtype)}, 'pending', "
                f"{sql_literal(priority)}, {tag()});")

    # extra readiness checks (only if missing for this project)
    for ctype, sev in EXTRA_CHECKS:
        sql.append(
            "INSERT INTO launch_readiness_checks (launch_project_id, check_type, check_status, severity, "
            "safe_summary, raw_context) "
            f"SELECT {sql_literal(pid)}, {sql_literal(ctype)}, 'pending', {sql_literal(sev)}, "
            f"'Phase 7.1 funnel readiness gate.', {tag()} "
            "WHERE NOT EXISTS (SELECT 1 FROM launch_readiness_checks WHERE launch_project_id = "
            f"{sql_literal(pid)} AND check_type = {sql_literal(ctype)});")

    sql.append("COMMIT;")
    code, out = run_psql("\n".join(sql))
    if code != 0:
        print(f"DB write FAILED (rolled back): {out[:400]}")
        return 2
    print(f"APPLIED: funnel workspace seeded for {args.launch_key} (tagged phase=7.1). "
          "send/publish disabled; no contacts selected; no messages sent; no external calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
