#!/usr/bin/env python3
"""Phase 7.15 — seed the DLF Wix UX / SEO / integration masterplan.

Planning-only seed. Creates one site experience blueprint, page blueprints,
integration readiness items, design component specs, and a human review queue for
the DLF Westpark website. It performs NO external calls (Wix/Meta/WhatsApp/email/
n8n/Google), NO publishing, NO live form/webhook creation, NO sends, and NO
inbound-lead/contact writes. Every integration stays external_call_allowed=false
and every page stays publish_enabled=false.

Dry-run by default. Writing requires BOTH --real-ok and --apply. It refuses if the
launch project is missing, and refuses duplicate Phase 7.15 rows unless
--allow-existing. Counts only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.15"
SOURCE = "dlf_wix_ux_integration_masterplan_seed"
BLUEPRINT_KEY = "dlf-westpark-wix-experience"

BASE_TAGS = {
    "phase": PHASE,
    "source": SOURCE,
    "external_calls_made": False,
    "publish_enabled": False,
    "communication_sent": False,
    "fable_handoff_future_phase": True,
}

# --- Site experience blueprint -------------------------------------------------

BLUEPRINT = {
    "blueprint_key": BLUEPRINT_KEY,
    "site_goal": (
        "Redesign the existing Wix site into a premium, mobile-first lead-generation "
        "and SEO system for DLF Westpark and future building launches."
    ),
    "target_audience": [
        "Andheri West / western-suburbs luxury home buyers",
        "NRI and investor buyers researching Mumbai luxury real estate",
        "Channel partners and referral sources",
    ],
    "primary_conversion_goals": [
        "Qualified lead form submissions (consent-based)",
        "WhatsApp enquiry click-throughs",
        "Brochure / detail requests routed to manual review",
    ],
    "seo_strategy_summary": (
        "Topical authority around DLF Westpark, Andheri West luxury property, and "
        "Mumbai luxury real estate via building pages, area pages, and a blog hub; "
        "factual claims (RERA/price/area) stay placeholder until verified."
    ),
    "design_direction": (
        "Apple-inspired (not copied) luxury real estate experience: clean, minimal, premium "
        "interface with large whitespace, strong visual hierarchy, beautiful typography, and "
        "image-first layouts. Neutral palette only - black / white / stone / charcoal with a "
        "restrained gold accent; soft contrast, no loud colors, no overstuffed cards, no broker-"
        "portal clutter or cheap real-estate template feel. Hero-first storytelling: one short "
        "headline, one primary CTA, one secondary CTA, and quiet trust markers. Mobile-first. The "
        "site should feel luxury, calm, trustworthy, and technically polished. No false scarcity "
        "or guaranteed-return language."
    ),
    "premium_visual_strategy": (
        "Cinematic property imagery driving scroll-based storytelling: each section reveals ONE "
        "idea (project identity -> location advantage -> lifestyle -> configuration interest -> "
        "investment/referral angle -> verified facts -> lead form) instead of dumping all details "
        "at once. Premium sans-serif typography with large headlines, restrained body text, "
        "generous line-height, and few font weights. Subtle motion only: scroll reveals, sticky "
        "CTA behavior, and smooth section transitions. Cards used only where useful; no crowded "
        "grids on landing pages."
    ),
    "threejs_component_strategy": (
        "Three.js / custom WebGL is OPTIONAL and used only as a lightweight premium accent within "
        "the hero - progressive enhancement with a static cinematic-image fallback. Hard "
        "constraints: must not block LCP, must not hurt mobile UX, and must never hide important "
        "text inside the canvas (SEO copy stays in the real DOM). Page speed and mobile "
        "performance remain publish blockers; heavy animation that harms speed/mobile/SEO is "
        "rejected. Final high-end UI is deferred to a future Fable handoff (Phase 7.16)."
    ),
}

# --- Page blueprints -----------------------------------------------------------
# Each row carries a review_type/priority used to build the review queue.

PAGES = [
    {
        "page_key": "home-refresh",
        "page_type": "homepage",
        "page_goal": "Refresh the existing homepage into a premium brand + lead entry point.",
        "seo_intent": "brand + navigational",
        "target_keyword": "Real Deal Housing",
        "suggested_slug": "/",
        "primary_cta": "Explore DLF Westpark",
        "required_sections": ["hero", "featured_launch", "trust_bar", "why_us", "lead_cta", "footer"],
        "integration_requirements": ["ga4", "google_tag_manager", "wix_forms"],
        "review_type": "ux_review", "priority": "high",
    },
    {
        "page_key": "dlf-westpark-landing",
        "page_type": "project_landing",
        "page_goal": "Primary DLF Westpark conversion experience.",
        "seo_intent": "transactional",
        "target_keyword": "DLF Westpark Andheri West",
        "suggested_slug": "/dlf-westpark-andheri-west",
        "primary_cta": "Request DLF Westpark details",
        "required_sections": ["hero", "highlights", "location", "lead_form", "faq", "disclaimer"],
        "integration_requirements": ["wix_forms", "n8n_webhook", "meta_pixel_capi", "whatsapp_chat"],
        "review_type": "conversion_review", "priority": "high",
    },
    {
        "page_key": "andheri-west-luxury-property",
        "page_type": "area_seo_page",
        "page_goal": "Rank for Andheri West luxury property intent and feed the project page.",
        "seo_intent": "commercial investigation",
        "target_keyword": "Andheri West luxury property",
        "suggested_slug": "/andheri-west-luxury-property",
        "primary_cta": "See featured projects",
        "required_sections": ["intro", "area_guide", "project_grid", "faq", "lead_cta"],
        "integration_requirements": ["ga4", "google_search_console"],
        "review_type": "seo_review", "priority": "high",
    },
    {
        "page_key": "mumbai-luxury-real-estate-guide",
        "page_type": "building_seo_page",
        "page_goal": "Topical authority hub for Mumbai luxury real estate.",
        "seo_intent": "informational + commercial",
        "target_keyword": "Mumbai luxury real estate",
        "suggested_slug": "/mumbai-luxury-real-estate-guide",
        "primary_cta": "Browse luxury projects",
        "required_sections": ["intro", "market_overview", "neighbourhood_links", "faq", "lead_cta"],
        "integration_requirements": ["ga4", "google_search_console"],
        "review_type": "seo_review", "priority": "high",
    },
    {
        "page_key": "dlf-westpark-blog-hub",
        "page_type": "blog_index",
        "page_goal": "Blog/content hub driving SEO and nurturing leads.",
        "seo_intent": "informational",
        "target_keyword": "Andheri West real estate blog",
        "suggested_slug": "/blog",
        "primary_cta": "Read the latest",
        "required_sections": ["blog_card_grid", "categories", "newsletter_optin_cta"],
        "integration_requirements": ["wix_cms", "ga4"],
        "review_type": "seo_review", "priority": "normal",
    },
    {
        "page_key": "lead-thank-you",
        "page_type": "thank_you_page",
        "page_goal": "Confirm submission and fire conversion tracking after review-gated capture.",
        "seo_intent": "noindex utility",
        "target_keyword": None,
        "suggested_slug": "/thank-you",
        "primary_cta": "Chat on WhatsApp",
        "required_sections": ["confirmation", "next_steps", "whatsapp_cta", "conversion_tracker"],
        "integration_requirements": ["meta_pixel_capi", "ga4", "google_tag_manager"],
        "review_type": "tracking_review", "priority": "high",
    },
    {
        "page_key": "privacy-consent",
        "page_type": "privacy_page",
        "page_goal": "Privacy policy + consent/opt-out basis for lead capture and messaging.",
        "seo_intent": "noindex utility",
        "target_keyword": None,
        "suggested_slug": "/privacy",
        "primary_cta": "Contact us",
        "required_sections": ["privacy_policy", "consent_basis", "data_rights", "contact"],
        "integration_requirements": [],
        "review_type": "ux_review", "priority": "normal",
    },
]

# --- Integration readiness items ----------------------------------------------
# external_call_required marks whether the integration ultimately needs a call;
# external_call_allowed stays false in this phase for every item.

INTEGRATIONS = [
    {
        "integration_key": "meta-pixel-capi", "integration_type": "meta_pixel_capi",
        "external_call_required": True, "contains_secret_required": True,
        "safe_summary": "Plan Meta Pixel + Conversions API; tokens/secrets stay out of repo. Not connected.",
        "review_type": "tracking_review", "priority": "high",
    },
    {
        "integration_key": "google-search-console", "integration_type": "google_search_console",
        "external_call_required": True, "contains_secret_required": False,
        "safe_summary": "Plan GSC property verification + sitemap submission. Not connected.",
        "review_type": "tracking_review", "priority": "normal",
    },
    {
        "integration_key": "ga4", "integration_type": "ga4",
        "external_call_required": True, "contains_secret_required": False,
        "safe_summary": "Plan GA4 property + key events. Not connected.",
        "review_type": "tracking_review", "priority": "normal",
    },
    {
        "integration_key": "gtm", "integration_type": "google_tag_manager",
        "external_call_required": True, "contains_secret_required": False,
        "safe_summary": "Plan GTM container for tags/triggers. Not connected.",
        "review_type": "tracking_review", "priority": "normal",
    },
    {
        "integration_key": "wix-forms", "integration_type": "wix_forms",
        "external_call_required": False, "contains_secret_required": False,
        "safe_summary": "Plan Wix native form mapped to review queue; no live form built.",
        "review_type": "integration_review", "priority": "high",
    },
    {
        "integration_key": "wix-cms", "integration_type": "wix_cms",
        "external_call_required": False, "contains_secret_required": False,
        "safe_summary": "Plan Wix CMS collections for blog/projects. No publishing.",
        "review_type": "integration_review", "priority": "normal",
    },
    {
        "integration_key": "n8n-webhook", "integration_type": "n8n_webhook",
        "external_call_required": True, "contains_secret_required": True,
        "safe_summary": "Plan n8n inactive lead-intake webhook path (Phase 7.11-7.13). No live webhook.",
        "review_type": "integration_review", "priority": "high",
    },
    {
        "integration_key": "whatsapp-chat", "integration_type": "whatsapp_chat",
        "external_call_required": False, "contains_secret_required": False,
        "safe_summary": "Plan click-to-WhatsApp CTA (consent-based). Not connected.",
        "review_type": "integration_review", "priority": "high",
    },
    {
        "integration_key": "whatsapp-business-platform", "integration_type": "whatsapp_business_platform",
        "external_call_required": True, "contains_secret_required": True,
        "safe_summary": "Plan WhatsApp Business Platform with approved templates + opt-in. Not connected.",
        "review_type": "integration_review", "priority": "high",
    },
    {
        "integration_key": "email-provider", "integration_type": "email_provider",
        "external_call_required": True, "contains_secret_required": True,
        "safe_summary": "Plan email campaign provider with consent + opt-out. Not connected.",
        "review_type": "integration_review", "priority": "normal",
    },
    {
        "integration_key": "crm-rdh-os-sync", "integration_type": "crm_sync",
        "external_call_required": False, "contains_secret_required": False,
        "safe_summary": "Plan sync of review-gated leads into Real Deal Housing OS / NocoDB. Internal only.",
        "review_type": "integration_review", "priority": "high",
    },
]

# --- Design component specs ----------------------------------------------------
# page_key links the component to a page blueprint (NULL for site-wide).

COMPONENTS = [
    {
        "component_key": "premium-hero", "component_type": "hero_section", "page_key": "dlf-westpark-landing",
        "design_goal": (
            "Apple-style hero-first storytelling: full-width cinematic hero with one short headline, "
            "one primary CTA + one secondary CTA, and quiet trust markers - calm, premium, uncluttered."
        ),
        "technical_notes": (
            "Static cinematic-image fallback first; subtle motion / scroll reveal optional. H1 and CTAs "
            "live in the real DOM (never inside canvas). Mobile-first; protect LCP."
        ),
        "performance_risk": "medium", "seo_risk": "low",
        "review_type": "design_review", "priority": "high",
    },
    {
        "component_key": "dlf-westpark-lead-form", "component_type": "lead_form", "page_key": "dlf-westpark-landing",
        "design_goal": (
            "Premium, trust-forward lead form that feels editorial - not spammy: minimal fields, "
            "visible privacy/consent language near the form, and brochure / price / site-visit intent "
            "capture."
        ),
        "technical_notes": (
            "Reuses Phase 7.14 field mappings; consent + opt-out visible near submit; no live webhook. "
            "Generous spacing and restrained typography; routed to the manual review queue."
        ),
        "performance_risk": "low", "seo_risk": "low",
        "review_type": "conversion_review", "priority": "high",
    },
    {
        "component_key": "sticky-whatsapp-cta", "component_type": "sticky_cta", "page_key": "dlf-westpark-landing",
        "design_goal": (
            "Minimal, high-converting sticky CTA: quiet click-to-WhatsApp (consent-based) that stays out "
            "of the way on desktop and becomes a mobile bottom CTA - premium, not pushy."
        ),
        "technical_notes": (
            "Deferred load; not connected to the WhatsApp API. Smooth show/hide on scroll; mobile "
            "bottom-bar behavior; respects reduced-motion."
        ),
        "performance_risk": "low", "seo_risk": "low",
        "review_type": "design_review", "priority": "normal",
    },
    {
        "component_key": "trust-verification-bar", "component_type": "trust_bar", "page_key": "dlf-westpark-landing",
        "design_goal": "Surface verified trust signals; RERA line stays placeholder.",
        "technical_notes": "No unverified claims rendered.",
        "performance_risk": "low", "seo_risk": "low",
        "review_type": "design_review", "priority": "normal",
    },
    {
        "component_key": "seo-faq", "component_type": "seo_faq", "page_key": "andheri-west-luxury-property",
        "design_goal": (
            "Clean, scannable SEO FAQ supporting clear H2 hierarchy and internal links to area / "
            "building / blog pages; answers high-intent questions while keeping the page calm and "
            "uncluttered."
        ),
        "technical_notes": (
            "Real DOM text (never canvas-hidden); optional FAQ schema only on verified content; internal "
            "links to area/building/blog pages. Page speed stays a publish blocker."
        ),
        "performance_risk": "low", "seo_risk": "medium",
        "review_type": "seo_review", "priority": "normal",
    },
    {
        "component_key": "location-lifestyle", "component_type": "location_map", "page_key": "dlf-westpark-landing",
        "design_goal": "Location + lifestyle context for Andheri West.",
        "technical_notes": "Lazy-load map embed; no third-party call until approved.",
        "performance_risk": "medium", "seo_risk": "low",
        "review_type": "performance_review", "priority": "normal",
    },
    {
        "component_key": "threejs-hero-visual", "component_type": "threejs_visual", "page_key": "dlf-westpark-landing",
        "design_goal": (
            "OPTIONAL lightweight premium WebGL hero accent in the Apple-inspired direction - a subtle "
            "motion layer over cinematic imagery, never the main content."
        ),
        "technical_notes": (
            "Progressive enhancement only; static cinematic fallback; must not block LCP, hurt mobile "
            "UX, or hide SEO copy inside the canvas. Gated by performance_review; heavy animation "
            "rejected."
        ),
        "performance_risk": "high", "seo_risk": "medium",
        "review_type": "performance_review", "priority": "high",
    },
    {
        "component_key": "blog-card-grid", "component_type": "blog_card_grid", "page_key": "dlf-westpark-blog-hub",
        "design_goal": "Scannable blog hub grid driving SEO + nurture.",
        "technical_notes": "Wix CMS-bound; no publishing in this phase.",
        "performance_risk": "low", "seo_risk": "low",
        "review_type": "design_review", "priority": "normal",
    },
    {
        "component_key": "thank-you-conversion-tracker", "component_type": "testimonial_block", "page_key": "lead-thank-you",
        "design_goal": "Fire conversion tracking after review-gated capture.",
        "technical_notes": "Tags stay disabled until tracking review approved.",
        "performance_risk": "low", "seo_risk": "low",
        "review_type": "tracking_review", "priority": "high",
    },
    {
        "component_key": "mobile-bottom-cta", "component_type": "sticky_cta", "page_key": None,
        "design_goal": "Mobile-first bottom CTA bar across key pages.",
        "technical_notes": "Mobile breakpoint only; deferred load.",
        "performance_risk": "low", "seo_risk": "low",
        "review_type": "performance_review", "priority": "normal",
    },
    {
        "component_key": "fable-design-handoff", "component_type": "hero_section", "page_key": None,
        "design_goal": "Placeholder for future Fable/Claude high-end UI/UX handoff.",
        "technical_notes": "Future phase: hand off a clean brief; no design produced now.",
        "performance_risk": "low", "seo_risk": "low",
        "review_type": "design_review", "priority": "normal",
    },
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


def lit(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    return "'" + str(value).replace("'", "''") + "'"


def jlit(value) -> str:
    """JSON/JSONB literal."""
    return "'" + json.dumps(value).replace("'", "''") + "'::jsonb"


def tags(extra: dict) -> str:
    merged = dict(BASE_TAGS)
    merged.update(extra)
    return jlit(merged)


def build_sql(launch_key: str, allow_existing: bool) -> str:
    lk = lit(launch_key)
    allow = "true" if allow_existing else "false"

    # Site experience blueprint insert.
    b = BLUEPRINT
    blueprint_insert = f"""
INSERT INTO wix_site_experience_blueprints
  (launch_project_id, blueprint_key, blueprint_status, site_goal, target_audience,
   primary_conversion_goals, seo_strategy_summary, design_direction, premium_visual_strategy,
   threejs_component_strategy, mobile_first_required, human_review_required, raw_context)
SELECT p.id, {lit(b['blueprint_key'])}, 'draft', {lit(b['site_goal'])}, {jlit(b['target_audience'])},
   {jlit(b['primary_conversion_goals'])}, {lit(b['seo_strategy_summary'])}, {lit(b['design_direction'])},
   {lit(b['premium_visual_strategy'])}, {lit(b['threejs_component_strategy'])}, true, true, {tags({})}
FROM launch_projects p WHERE p.launch_key = {lk};
"""

    page_inserts = []
    for pg in PAGES:
        page_inserts.append(f"""
INSERT INTO wix_page_blueprints
  (launch_project_id, site_experience_blueprint_id, page_key, page_type, page_status, page_goal,
   seo_intent, target_keyword, suggested_slug, primary_cta, required_sections,
   integration_requirements, publish_enabled, human_review_required, raw_context)
SELECT p.id, seb.id, {lit(pg['page_key'])}, {lit(pg['page_type'])}, 'draft', {lit(pg['page_goal'])},
   {lit(pg['seo_intent'])}, {lit(pg['target_keyword'])}, {lit(pg['suggested_slug'])}, {lit(pg['primary_cta'])},
   {jlit(pg['required_sections'])}, {jlit(pg['integration_requirements'])}, false, true, {tags({})}
FROM launch_projects p
JOIN wix_site_experience_blueprints seb ON seb.launch_project_id = p.id AND seb.blueprint_key = {lit(BLUEPRINT_KEY)}
WHERE p.launch_key = {lk};
""")

    integration_inserts = []
    for ig in INTEGRATIONS:
        integration_inserts.append(f"""
INSERT INTO wix_integration_readiness_items
  (launch_project_id, integration_key, integration_type, readiness_status, external_call_required,
   external_call_allowed, contains_secret_required, human_review_required, safe_summary, raw_context)
SELECT p.id, {lit(ig['integration_key'])}, {lit(ig['integration_type'])}, 'planned', {lit(ig['external_call_required'])},
   false, {lit(ig['contains_secret_required'])}, true, {lit(ig['safe_summary'])}, {tags({})}
FROM launch_projects p WHERE p.launch_key = {lk};
""")

    component_inserts = []
    for cp in COMPONENTS:
        page_join = ""
        page_id_expr = "NULL"
        if cp["page_key"] is not None:
            page_id_expr = "pb.id"
            page_join = (
                f"JOIN wix_page_blueprints pb ON pb.launch_project_id = p.id "
                f"AND pb.page_key = {lit(cp['page_key'])}"
            )
        component_inserts.append(f"""
INSERT INTO wix_design_component_specs
  (launch_project_id, page_blueprint_id, component_key, component_type, component_status, design_goal,
   content_requirements, technical_notes, performance_risk, seo_risk, human_review_required, raw_context)
SELECT p.id, {page_id_expr}, {lit(cp['component_key'])}, {lit(cp['component_type'])}, 'draft', {lit(cp['design_goal'])},
   '[]'::jsonb, {lit(cp['technical_notes'])}, {lit(cp['performance_risk'])}, {lit(cp['seo_risk'])}, true, {tags({})}
FROM launch_projects p {page_join}
WHERE p.launch_key = {lk};
""")

    # Review items: one per page, integration, component, plus two site-level.
    review_inserts = []

    # Site-level blueprint UX review + publish blocker.
    review_inserts.append(f"""
INSERT INTO wix_ux_review_items
  (launch_project_id, site_experience_blueprint_id, review_type, status, priority, raw_context)
SELECT p.id, seb.id, 'ux_review', 'pending', 'high', {tags({'scope': 'site_experience'})}
FROM launch_projects p
JOIN wix_site_experience_blueprints seb ON seb.launch_project_id = p.id AND seb.blueprint_key = {lit(BLUEPRINT_KEY)}
WHERE p.launch_key = {lk};
""")
    review_inserts.append(f"""
INSERT INTO wix_ux_review_items
  (launch_project_id, site_experience_blueprint_id, review_type, status, priority, raw_context)
SELECT p.id, seb.id, 'publish_blocker_review', 'pending', 'blocker', {tags({'scope': 'publish_blocker'})}
FROM launch_projects p
JOIN wix_site_experience_blueprints seb ON seb.launch_project_id = p.id AND seb.blueprint_key = {lit(BLUEPRINT_KEY)}
WHERE p.launch_key = {lk};
""")

    for pg in PAGES:
        review_inserts.append(f"""
INSERT INTO wix_ux_review_items
  (launch_project_id, page_blueprint_id, review_type, status, priority, raw_context)
SELECT p.id, pb.id, {lit(pg['review_type'])}, 'pending', {lit(pg['priority'])}, {tags({'scope': 'page', 'page_key': pg['page_key']})}
FROM launch_projects p
JOIN wix_page_blueprints pb ON pb.launch_project_id = p.id AND pb.page_key = {lit(pg['page_key'])}
WHERE p.launch_key = {lk};
""")

    for ig in INTEGRATIONS:
        review_inserts.append(f"""
INSERT INTO wix_ux_review_items
  (launch_project_id, integration_readiness_item_id, review_type, status, priority, raw_context)
SELECT p.id, iri.id, {lit(ig['review_type'])}, 'pending', {lit(ig['priority'])}, {tags({'scope': 'integration', 'integration_key': ig['integration_key']})}
FROM launch_projects p
JOIN wix_integration_readiness_items iri ON iri.launch_project_id = p.id AND iri.integration_key = {lit(ig['integration_key'])}
WHERE p.launch_key = {lk};
""")

    for cp in COMPONENTS:
        review_inserts.append(f"""
INSERT INTO wix_ux_review_items
  (launch_project_id, design_component_spec_id, review_type, status, priority, raw_context)
SELECT p.id, dcs.id, {lit(cp['review_type'])}, 'pending', {lit(cp['priority'])}, {tags({'scope': 'design_component', 'component_key': cp['component_key']})}
FROM launch_projects p
JOIN wix_design_component_specs dcs ON dcs.launch_project_id = p.id AND dcs.component_key = {lit(cp['component_key'])}
WHERE p.launch_key = {lk};
""")

    body = blueprint_insert + "".join(page_inserts) + "".join(integration_inserts) \
        + "".join(component_inserts) + "".join(review_inserts)

    return f"""
BEGIN;

DO $GUARD$
DECLARE proj int; existing int;
BEGIN
  SELECT count(*) INTO proj FROM launch_projects WHERE launch_key = {lk};
  IF proj = 0 THEN RAISE EXCEPTION 'Refusing: launch project % not found.', {lk}; END IF;
  SELECT count(*) INTO existing
  FROM wix_site_experience_blueprints seb
  JOIN launch_projects p ON p.id = seb.launch_project_id
  WHERE p.launch_key = {lk}
    AND seb.raw_context->>'phase' = '{PHASE}'
    AND seb.raw_context->>'source' = '{SOURCE}';
  IF existing > 0 AND NOT {allow} THEN
    RAISE EXCEPTION 'Refusing: Phase 7.15 masterplan rows already exist (use --allow-existing).';
  END IF;
END $GUARD$;

{body}

DO $LIVE_GUARD$
DECLARE ext int; pub int; act int; inbound int; contacts_count int; send_count int; publish_count int;
BEGIN
  SELECT count(*) INTO ext FROM wix_integration_readiness_items iri JOIN launch_projects p ON p.id = iri.launch_project_id
    WHERE p.launch_key = {lk} AND iri.external_call_allowed;
  SELECT count(*) INTO pub FROM wix_page_blueprints pb JOIN launch_projects p ON p.id = pb.launch_project_id
    WHERE p.launch_key = {lk} AND pb.publish_enabled;
  SELECT count(*) INTO act FROM wix_integration_readiness_items iri JOIN launch_projects p ON p.id = iri.launch_project_id
    WHERE p.launch_key = {lk} AND iri.readiness_status IN ('active', 'connected_manually');
  SELECT count(*) INTO inbound FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  SELECT send_enabled_count INTO send_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT publish_enabled_count INTO publish_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  IF ext > 0 THEN RAISE EXCEPTION 'Refusing: an integration is marked external_call_allowed.'; END IF;
  IF pub > 0 THEN RAISE EXCEPTION 'Refusing: a page is marked publish_enabled.'; END IF;
  IF act > 0 THEN RAISE EXCEPTION 'Refusing: an integration is marked active/connected.'; END IF;
  IF inbound <> 0 THEN RAISE EXCEPTION 'Refusing: inbound lead count changed to %.', inbound; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 THEN RAISE EXCEPTION 'Refusing: send/publish enabled.'; END IF;
END $LIVE_GUARD$;

COMMIT;

SELECT 'site_experience_blueprints', count(*)::text FROM wix_site_experience_blueprints seb JOIN launch_projects p ON p.id = seb.launch_project_id WHERE p.launch_key = {lk} AND seb.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'page_blueprints', count(*)::text FROM wix_page_blueprints pb JOIN launch_projects p ON p.id = pb.launch_project_id WHERE p.launch_key = {lk} AND pb.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'integration_readiness_items', count(*)::text FROM wix_integration_readiness_items iri JOIN launch_projects p ON p.id = iri.launch_project_id WHERE p.launch_key = {lk} AND iri.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'design_component_specs', count(*)::text FROM wix_design_component_specs dcs JOIN launch_projects p ON p.id = dcs.launch_project_id WHERE p.launch_key = {lk} AND dcs.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'review_items', count(*)::text FROM wix_ux_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'external_call_allowed_count', external_call_allowed_count::text FROM vw_dlf_wix_unified_experience_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'publish_enabled_count', publish_enabled_count::text FROM vw_dlf_wix_unified_experience_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_to_publish', ready_to_publish::text FROM vw_dlf_wix_unified_experience_readiness WHERE launch_key = {lk}
ORDER BY 1;
"""


def build_refresh_sql(launch_key: str) -> str:
    """Update design-direction text on EXISTING Phase 7.15 rows from the constants.

    Idempotent UPDATEs only - no inserts, no new rows, no status/flag changes. Keeps
    the live blueprint + design components in sync with the masterplan definition
    after the Apple-inspired design direction was added.
    """
    lk = lit(launch_key)
    b = BLUEPRINT
    parts = [f"""
BEGIN;

DO $GUARD$
DECLARE proj int; bp int;
BEGIN
  SELECT count(*) INTO proj FROM launch_projects WHERE launch_key = {lk};
  IF proj = 0 THEN RAISE EXCEPTION 'Refusing: launch project % not found.', {lk}; END IF;
  SELECT count(*) INTO bp
  FROM wix_site_experience_blueprints seb JOIN launch_projects p ON p.id = seb.launch_project_id
  WHERE p.launch_key = {lk} AND seb.raw_context->>'phase' = '{PHASE}'
    AND seb.raw_context->>'source' = '{SOURCE}' AND seb.blueprint_key = {lit(BLUEPRINT_KEY)};
  IF bp = 0 THEN RAISE EXCEPTION 'Refusing: no Phase 7.15 blueprint to refresh (seed it first).'; END IF;
END $GUARD$;

UPDATE wix_site_experience_blueprints seb
SET design_direction = {lit(b['design_direction'])},
    premium_visual_strategy = {lit(b['premium_visual_strategy'])},
    threejs_component_strategy = {lit(b['threejs_component_strategy'])}
FROM launch_projects p
WHERE seb.launch_project_id = p.id AND p.launch_key = {lk}
  AND seb.blueprint_key = {lit(BLUEPRINT_KEY)}
  AND seb.raw_context->>'phase' = '{PHASE}' AND seb.raw_context->>'source' = '{SOURCE}';
"""]
    for cp in COMPONENTS:
        parts.append(f"""
UPDATE wix_design_component_specs dcs
SET design_goal = {lit(cp['design_goal'])},
    technical_notes = {lit(cp['technical_notes'])}
FROM launch_projects p
WHERE dcs.launch_project_id = p.id AND p.launch_key = {lk}
  AND dcs.component_key = {lit(cp['component_key'])}
  AND dcs.raw_context->>'phase' = '{PHASE}' AND dcs.raw_context->>'source' = '{SOURCE}';
""")
    parts.append(f"""
DO $LIVE_GUARD$
DECLARE ext int; pub int; act int; inbound int; contacts_count int; send_count int; publish_count int;
BEGIN
  SELECT count(*) INTO ext FROM wix_integration_readiness_items iri JOIN launch_projects p ON p.id = iri.launch_project_id
    WHERE p.launch_key = {lk} AND iri.external_call_allowed;
  SELECT count(*) INTO pub FROM wix_page_blueprints pb JOIN launch_projects p ON p.id = pb.launch_project_id
    WHERE p.launch_key = {lk} AND pb.publish_enabled;
  SELECT count(*) INTO act FROM wix_integration_readiness_items iri JOIN launch_projects p ON p.id = iri.launch_project_id
    WHERE p.launch_key = {lk} AND iri.readiness_status IN ('active', 'connected_manually');
  SELECT count(*) INTO inbound FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  SELECT send_enabled_count INTO send_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT publish_enabled_count INTO publish_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  IF ext > 0 THEN RAISE EXCEPTION 'Refusing: an integration is marked external_call_allowed.'; END IF;
  IF pub > 0 THEN RAISE EXCEPTION 'Refusing: a page is marked publish_enabled.'; END IF;
  IF act > 0 THEN RAISE EXCEPTION 'Refusing: an integration is marked active/connected.'; END IF;
  IF inbound <> 0 THEN RAISE EXCEPTION 'Refusing: inbound lead count changed to %.', inbound; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 THEN RAISE EXCEPTION 'Refusing: send/publish enabled.'; END IF;
END $LIVE_GUARD$;

COMMIT;

SELECT 'blueprint_design_direction_updated', count(*)::text FROM wix_site_experience_blueprints seb JOIN launch_projects p ON p.id = seb.launch_project_id WHERE p.launch_key = {lk} AND seb.blueprint_key = {lit(BLUEPRINT_KEY)} AND seb.design_direction LIKE 'Apple-inspired%'
UNION ALL SELECT 'components_refreshed', count(*)::text FROM wix_design_component_specs dcs JOIN launch_projects p ON p.id = dcs.launch_project_id WHERE p.launch_key = {lk} AND dcs.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'external_call_allowed_count', external_call_allowed_count::text FROM vw_dlf_wix_unified_experience_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'publish_enabled_count', publish_enabled_count::text FROM vw_dlf_wix_unified_experience_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_to_publish', ready_to_publish::text FROM vw_dlf_wix_unified_experience_readiness WHERE launch_key = {lk}
ORDER BY 1;
""")
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed DLF Wix UX/SEO/integration masterplan. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--allow-existing", action="store_true")
    parser.add_argument("--refresh-design", action="store_true",
                        help="Update design-direction text on existing Phase 7.15 rows instead of inserting.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    if args.refresh_design:
        print(f"DLF Wix masterplan design-direction refresh. launch_key={args.launch_key}. Counts only.")
        print("projected (UPDATE existing Phase 7.15 rows; no inserts):")
        print("  blueprint design fields: design_direction, premium_visual_strategy, threejs_component_strategy")
        print(f"  design components refreshed: {len(COMPONENTS)}")
        print("  external_call_allowed: 0   publish_enabled: 0   integrations_active: 0")
        print("  new rows: 0   inbound_leads: 0   contacts unchanged   messages_sent: 0")
        if not (args.apply and args.real_ok):
            print("Dry run only. No database writes were made.")
            print("Writing requires BOTH --real-ok and --apply.")
            return 0
        code, output = run_psql(build_refresh_sql(args.launch_key))
        print("Refresh result:" if code == 0 else "Refresh FAILED:")
        print(output)
        return code

    print(f"DLF Wix UX/SEO/integration masterplan seed. launch_key={args.launch_key}. Counts only.")
    print("projected:")
    print("  site experience blueprints: 1")
    print(f"  page blueprints: {len(PAGES)}")
    print(f"  integration readiness items: {len(INTEGRATIONS)}")
    print(f"  design component specs: {len(COMPONENTS)}")
    print(f"  review items: {2 + len(PAGES) + len(INTEGRATIONS) + len(COMPONENTS)}")
    print("  external_call_allowed: 0   publish_enabled: 0   integrations_active: 0")
    print("  wix_api_calls: 0   meta/whatsapp/email/n8n/google_api_calls: 0")
    print("  publishing: 0   live_forms: 0   live_webhooks: 0")
    print("  inbound_leads_created: 0   contacts_created_or_merged: 0   messages_sent: 0")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(build_sql(args.launch_key, args.allow_existing))
    print("Apply result:" if code == 0 else "Apply FAILED:")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
