#!/usr/bin/env python3
"""Phase 7.23 - create the DLF Wix AI build execution plan.

Dry-run by default. Generates code/artifact files under ignored exports/ and records a
review-gated execution plan for building the blank Wix Studio staging site with AI assistance.

This script does not call Wix APIs, read/store Wix API keys, install Wix CLI, connect GitHub,
publish, create forms/webhooks/tracking, or touch inbound leads/contacts/messages. Counts only;
never prints the staging URL.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.23"
SOURCE = "dlf_wix_ai_build_plan"
ARTIFACT_SUBDIR = "dlf-westpark-gallery-white-v1"
ALLOWED_ROUTES = ("auto", "wix_git_cli", "wix_custom_element_velo", "wix_code_snippet")

SECTIONS = (
    "nav", "hero", "project", "location", "lifestyle", "residences", "perspective",
    "verified_facts", "enquiry", "faq", "footer", "sticky_cta",
)
PLACEHOLDERS = (
    "RERA_VERIFY", "PRICE_VERIFY", "BROCHURE_LINK_PENDING", "WIX_PAGE_PENDING",
    "VERIFY", "VISUAL_DIRECTION_PENDING",
)
def json_literal(value) -> str:
    return sql_literal(json.dumps(value, sort_keys=True))
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH proj AS (
  SELECT id FROM launch_projects WHERE launch_key = {lk}
),
site AS (
  SELECT s.*
  FROM wix_staging_sites s
  WHERE s.launch_project_id IN (SELECT id FROM proj)
  ORDER BY s.created_at DESC
  LIMIT 1
)
SELECT
  (SELECT count(*) FROM proj),
  (SELECT count(*) FROM site),
  (SELECT count(*) FROM site WHERE real_domain_connected OR public_indexing_enabled OR page_published OR live_form_created OR live_webhook_created OR external_tracking_enabled OR wix_api_call_made),
  (SELECT count(*) FROM wix_ai_build_execution_plans e WHERE e.launch_project_id IN (SELECT id FROM proj) AND e.raw_context->>'phase' = '{PHASE}' AND e.raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM wix_api_permission_catalog),
  (SELECT count(*) FROM wix_api_key_profiles WHERE profile_status = 'active' OR secret_value_stored OR external_call_allowed),
  (SELECT count(*) FROM inbound_leads),
  (SELECT count(*) FROM contacts),
  (SELECT send_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT publish_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT communication_sent FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT ready_for_fake_lead_test::text FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk}),
  (SELECT ready_for_production_publish::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk});
"""

def permission_summary_sql() -> str:
    return """
SELECT recommended_status || '|' || risk_level || '|' || count(*)
FROM wix_api_permission_catalog
GROUP BY recommended_status, risk_level
ORDER BY recommended_status, risk_level;
"""

def choose_route(preferred_route: str) -> tuple[str, str, str, list[str], list[str], list[str], list[str]]:
    if preferred_route == "auto":
        route = "wix_git_cli"
    else:
        route = preferred_route
    if route == "wix_git_cli":
        status = "needs_operator_setup"
        fallback = "wix_custom_element_velo"
        now: list[str] = []
        later = ["wix_cli_git_integration", "manage_site_branches", "read_site_urls"]
        blockers = ["operator must confirm Git Integration + Wix CLI for Sites is available on the staging site"]
        setup = ["connect the Wix site to GitHub", "clone the generated repository", "run Wix CLI locally when permitted"]
    elif route == "wix_custom_element_velo":
        status = "ready_for_custom_element_build"
        fallback = "wix_code_snippet"
        now = []
        later = ["custom_embeds", "manage_embedded_scripts"]
        blockers = ["operator must enable Velo/dev mode and add one Custom Element if Git/CLI is unavailable"]
        setup = ["enable Velo/dev mode", "add one Custom Element", "paste generated JS/CSS into the Wix-hosted element"]
    else:
        status = "ready_for_snippet_paste"
        fallback = "wix_api_later"
        now = []
        later = []
        blockers = ["snippet route has weaker SEO/layout integration and should only be used if Git/CLI and Custom Element routes are unavailable"]
        setup = ["paste generated HTML/CSS/JS into the safest Wix-supported embed surface"]
    forbidden = [
        "publish_metasite", "all_site_permissions", "wix_contacts_members_write",
        "manage_marketing_tags", "manage_embedded_scripts_now", "email_marketing_send",
        "social_posting", "payments", "members", "bookings", "ecommerce",
    ]
    return route, fallback, status, now, later, forbidden, blockers + setup

def artifact_texts(route: str) -> dict[str, tuple[str, str]]:
    copy_blocks = "\n".join([
        "# Gallery White Copy Blocks",
        "",
        "Sections: " + ", ".join(SECTIONS),
        "",
        "Hero: DLF Westpark, Andheri West. A calmer way to evaluate a premium city residence.",
        "Project: Gallery White uses structured, verifiable content blocks and restrained visual rhythm.",
        "Location: commute, schools, retail, and lifestyle notes stay human-reviewable until verified.",
        "Residences: price and availability remain `PRICE_VERIFY`; RERA remains `RERA_VERIFY`.",
        "Perspective: a quiet editorial chapter for context, buyer intent, and next-step clarity.",
        "Verified facts: `VERIFY`, `BROCHURE_LINK_PENDING`, `WIX_PAGE_PENDING`, `VISUAL_DIRECTION_PENDING` stay visible until replaced by approved facts.",
        "FAQ: SEO text is in the DOM and never rendered as canvas text.",
    ])
    css = """
:host{all:initial;display:block;font-family:Manrope,Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#17313c;background:#fff}
*{box-sizing:border-box} .gw-page{background:#fff;color:#17313c;line-height:1.5}
.gw-nav{position:sticky;top:0;z-index:5;display:flex;align-items:center;justify-content:space-between;padding:18px clamp(20px,5vw,72px);background:rgba(255,255,255,.92);backdrop-filter:blur(16px);border-bottom:1px solid #e9eef0}
.gw-logo{font-weight:700;letter-spacing:.04em}.gw-links{display:flex;gap:22px;font-size:14px}.gw-links a{color:#244756;text-decoration:none}
.gw-hero{min-height:78vh;display:grid;grid-template-columns:minmax(0,1.1fr) minmax(280px,.9fr);gap:clamp(28px,5vw,72px);align-items:center;padding:clamp(64px,8vw,112px) clamp(20px,6vw,86px)}
.gw-kicker{color:#b85052;text-transform:uppercase;font-size:12px;letter-spacing:.18em}.gw-hero h1{font-size:clamp(44px,7vw,94px);line-height:.96;margin:16px 0;color:#1f3d4d;letter-spacing:0}
.gw-lede{font-size:clamp(18px,2vw,24px);max-width:720px;color:#395661}.gw-actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}
.gw-btn{display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:0 20px;border:1px solid #1f3d4d;background:#1f3d4d;color:white;text-decoration:none;border-radius:2px;font-weight:650}
.gw-btn.secondary{background:white;color:#1f3d4d}.gw-visual{aspect-ratio:4/5;border:1px solid #dfe8eb;background:linear-gradient(135deg,#f5f8f8,#e9eff1);display:grid;place-items:center;color:#58717b}
.gw-section{padding:clamp(58px,7vw,108px) clamp(20px,6vw,86px);border-top:1px solid #edf1f2}.gw-section h2{font-size:clamp(30px,4vw,58px);line-height:1.02;color:#1f3d4d;margin:0 0 18px;letter-spacing:0}
.gw-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.gw-card{border:1px solid #e4eaed;padding:24px;min-height:160px;background:#fff}.gw-token{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:#8a4b4b;background:#fff4f1;padding:2px 6px}
.gw-dark{background:#1f3d4d;color:white}.gw-dark h2{color:white}.gw-dark .gw-card{background:rgba(255,255,255,.06);border-color:rgba(255,255,255,.18)}
.gw-form{display:grid;gap:14px;max-width:720px}.gw-form input,.gw-form select,.gw-form textarea{width:100%;min-height:48px;border:1px solid #d8e1e5;background:#f7fafb;padding:12px 14px;font:inherit;color:#17313c}
.gw-consent{display:flex;gap:10px;align-items:flex-start;font-size:13px;color:#506873}.gw-consent input{margin-top:3px}.gw-faq details{border-top:1px solid #dfe7ea;padding:18px 0}.gw-faq summary{cursor:pointer;font-weight:650;color:#1f3d4d}
.gw-footer{padding:40px clamp(20px,6vw,86px);background:#f7f9f9;color:#536b75}.gw-sticky{position:fixed;left:0;right:0;bottom:0;display:none;grid-template-columns:1fr 1fr;z-index:6;background:white;border-top:1px solid #dfe7ea}.gw-sticky a{padding:14px;text-align:center;text-decoration:none;color:#1f3d4d;font-weight:700}
@media(max-width:820px){.gw-links{display:none}.gw-hero{grid-template-columns:1fr;padding-bottom:92px}.gw-grid{grid-template-columns:1fr}.gw-sticky{display:grid}.gw-section{padding-block:54px}.gw-hero h1{font-size:44px}}
""".strip()
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DLF Westpark Andheri West - Gallery White Preview</title>
  <meta name="description" content="Preview-only DLF Westpark staging page with verified placeholders, DOM SEO text, and no live form or tracking.">
  <link rel="stylesheet" href="gallery-white-static-preview.css">
</head>
<body>
  <gallery-white-page></gallery-white-page>
  <script src="gallery-white-custom-element.js"></script>
</body>
</html>
"""
    js = f"""
class GalleryWhitePage extends HTMLElement {{
  connectedCallback() {{
    this.innerHTML = `
      <main class="gw-page">
        <nav class="gw-nav" data-section="nav"><div class="gw-logo">DLF Westpark</div><div class="gw-links"><a href="#project">Project</a><a href="#location">Location</a><a href="#residences">Residences</a><a href="#enquiry">Enquiry</a></div></nav>
        <section class="gw-hero" data-section="hero"><div><div class="gw-kicker">Gallery White / staging preview</div><h1>DLF Westpark, Andheri West</h1><p class="gw-lede">A quiet, verification-first landing page for evaluating a premium city residence. No live form, no tracking, no production publish.</p><div class="gw-actions"><a class="gw-btn" href="#enquiry">Request details</a><a class="gw-btn secondary" href="#verified_facts">View verified facts</a></div></div><div class="gw-visual">VISUAL_DIRECTION_PENDING</div></section>
        <section id="project" class="gw-section" data-section="project"><h2>Project rhythm, not sales noise.</h2><div class="gw-grid"><article class="gw-card">Premium white-space-led page architecture.</article><article class="gw-card">Brand grounded in deep teal with restrained warm facets.</article><article class="gw-card">All unverified facts remain visible placeholders.</article></div></section>
        <section id="location" class="gw-section" data-section="location"><h2>Location context for Andheri West.</h2><p>Transit, schools, retail, and lifestyle context will be verified before production. Current status: <span class="gw-token">VERIFY</span>.</p></section>
        <section class="gw-section gw-dark" data-section="lifestyle"><h2>Lifestyle, filtered through restraint.</h2><p>Gallery White favors editorial calm over visual clutter, keeping the focus on buyer intent and factual confidence.</p></section>
        <section id="residences" class="gw-section" data-section="residences"><h2>Residences with honest status.</h2><div class="gw-grid"><article class="gw-card">Configuration details: <span class="gw-token">VERIFY</span></article><article class="gw-card">Price guidance: <span class="gw-token">PRICE_VERIFY</span></article><article class="gw-card">Brochure: <span class="gw-token">BROCHURE_LINK_PENDING</span></article></div></section>
        <section class="gw-section" data-section="perspective"><h2>Perspective before enquiry.</h2><p>The page should help a serious buyer understand what is verified, what is pending, and what the operator will confirm manually.</p></section>
        <section id="verified_facts" class="gw-section" data-section="verified_facts"><h2>Verified facts ledger.</h2><div class="gw-grid"><article class="gw-card">RERA: <span class="gw-token">RERA_VERIFY</span></article><article class="gw-card">Wix page: <span class="gw-token">WIX_PAGE_PENDING</span></article><article class="gw-card">Status: <span class="gw-token">VERIFY</span></article></div></section>
        <section id="enquiry" class="gw-section" data-section="enquiry"><h2>Request details.</h2><form class="gw-form" aria-label="Preview-only enquiry form"><input placeholder="Name (preview only)"><input placeholder="Phone or email (do not submit real data yet)"><select><option>Buying intent</option><option>Request brochure</option><option>Ask for price verification</option></select><textarea placeholder="Message"></textarea><label class="gw-consent"><input type="checkbox"> I consent to be contacted after human review. Unchecked by default.</label><label class="gw-consent"><input type="checkbox"> I agree to privacy terms after review. Unchecked by default.</label><button class="gw-btn" type="button">Preview only - no live submission</button></form></section>
        <section class="gw-section gw-faq" data-section="faq"><h2>FAQ</h2><details><summary>Is this page live?</summary><p>No. This is a staging preview with no publish, live webhook, or tracking.</p></details><details><summary>Are facts verified?</summary><p>Only verified facts should replace placeholders such as RERA_VERIFY, PRICE_VERIFY, and VERIFY.</p></details></section>
        <footer class="gw-footer" data-section="footer">DLF Westpark staging preview. Production publish remains blocked.</footer>
        <div class="gw-sticky" data-section="sticky_cta"><a href="#enquiry">Request details</a><a href="#verified_facts">Verify facts</a></div>
      </main>`;
  }}
}}
customElements.define("gallery-white-page", GalleryWhitePage);
""".strip()
    page_code = """
// Gallery White Velo page-code notes.
// Use only after human review. No live webhook, no tracking, no API key, no publish action.
$w.onReady(function () {
  // Optional: wire intent buttons to preselect a local form dropdown inside Wix.
  // Keep consent checkboxes unchecked by default.
  // Do not submit to live automations in this phase.
});
""".strip()
    permission_analysis = """
# Wix Permission Route Analysis

Preferred visual build route: Wix Git Integration + Wix CLI for Sites, if available.

Official docs reviewed:
- Git Integration & Wix CLI for Sites lets developers connect a Wix site to GitHub, code in an IDE, test with Local Editor, and preview/publish with CLI. Publishing remains forbidden for this phase.
- Wix APIs are suitable for data, CRM/contact, media, forms, blog, FAQ, branches, analytics, and automation capabilities. They are not assumed to be the pixel-perfect layout builder for this MVP.

Now: no Wix API key is required. Operator setup may be required for Git Integration/Wix CLI.
Later: CMS/forms/media/blog/FAQ/branches can use the Phase 7.21 staging key profiles after approval.
Forbidden now: Publish Metasite, All site permissions, Contacts/Members writes, Marketing Tag writes, Embedded Scripts, email/social sends, payments, ecommerce, bookings, members.
""".strip()
    readme = f"""
# DLF Westpark Gallery White AI Build Package

Generated for Phase 7.23. Preferred route: `{route}`.

This package is for staging implementation review only. It contains no Wix API key, no live webhook,
no tracking script, no real contact data, and no production publish code.

Use order:
1. Review `wix-permission-route-analysis.md`.
2. Try Git Integration + Wix CLI for Sites if available.
3. If unavailable, use the Wix-hosted Custom Element/Velo route.
4. Use snippet/embed fallback only if the first two routes are unavailable.
""".strip()
    form_config = """
# Gallery White Form Config

- Preview/staging only.
- Consent checkboxes unchecked by default.
- No live webhook URL.
- No external automation.
- Fields: name, contact method, buying intent, message, consent_contact, consent_privacy.
- Submit button label: Preview only - no live submission.
""".strip()
    seo_meta = """
# Gallery White SEO Meta

Title: DLF Westpark Andheri West - Premium Residences Preview
Description: Review DLF Westpark in Andheri West with verified placeholders, location context, residence notes, and a preview-only enquiry form.
H1: DLF Westpark, Andheri West
H2 sections: Project, Location, Lifestyle, Residences, Perspective, Verified Facts, Enquiry, FAQ.
SEO text must stay in DOM. No canvas text.
""".strip()
    setup = """
# Wix Git CLI Setup Checklist

- Confirm Git Integration + Wix CLI for Sites is available on the blank staging site.
- Connect the Wix site to GitHub only after operator approval.
- Clone the Wix repository locally only after setup is complete.
- Do not run publish commands.
- Keep production domain disconnected and indexing disabled.
- If Git/CLI is unavailable, use Custom Element + Velo fallback.
""".strip()
    return {
        "implementation-readme.md": ("implementation_readme", readme),
        "wix-permission-route-analysis.md": ("permission_route_analysis", permission_analysis),
        "wix-git-cli-setup-checklist.md": ("wix_cli_setup_notes", setup),
        "gallery-white-custom-element.js": ("custom_element_js", js),
        "gallery-white-custom-element.css": ("custom_element_css", css),
        "gallery-white-page-code.js": ("velo_page_code", page_code),
        "gallery-white-copy-blocks.md": ("copy_blocks", copy_blocks),
        "gallery-white-form-config.md": ("form_config", form_config),
        "gallery-white-seo-meta.md": ("seo_meta", seo_meta),
        "gallery-white-static-preview.html": ("static_preview_html", html),
        "gallery-white-static-preview.css": ("static_preview_css", css),
    }

def validate_artifacts(artifacts: dict[str, tuple[str, str]]) -> dict[str, str]:
    all_text = "\n".join(text for _, text in artifacts.values())
    checks = {
        "no_contact_data": not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\+?\d[\d ().-]{8,}\d", all_text),
        "no_secrets": not re.search(r"(?i)(api[_-]?key\s*=|secret\s*=|password\s*=|token\s*=)", all_text),
        "no_api_key": "API_KEY" not in all_text and "apiKey" not in all_text,
        "no_live_webhook": "webhook_url" not in all_text.lower() and "https://hooks." not in all_text.lower(),
        "no_publish_code": "publish(" not in all_text,
        "placeholders_preserved": all(token in all_text for token in PLACEHOLDERS),
        "gallery_white_sections_present": all(section in all_text for section in SECTIONS),
        "seo_text_in_dom": "<h1>" in all_text and "<h2>" in all_text and "<canvas" not in all_text.lower(),
        "mobile_css_present": "@media(max-width:820px)" in all_text and "gw-sticky" in all_text,
        "custom_element_safe": "customElements.define" in all_text and "fetch(" not in all_text,
        "velo_safe": "publish(" not in artifacts["gallery-white-page-code.js"][1].lower(),
        "no_external_tracking": "gtag(" not in all_text and "fbq(" not in all_text and "googletagmanager" not in all_text.lower(),
        "permission_analysis_present": "Preferred visual build route" in all_text,
    }
    return {key: ("passed" if ok else "failed") for key, ok in checks.items()}

def write_artifacts(output_dir: Path, artifacts: dict[str, tuple[str, str]], apply: bool) -> list[tuple[str, str, str]]:
    target = output_dir / ARTIFACT_SUBDIR
    rows = []
    for filename, (artifact_type, text) in artifacts.items():
        path = target / filename
        if apply:
            target.mkdir(parents=True, exist_ok=True)
            path.write_text(text.rstrip() + "\n", encoding="utf-8")
        rel = path.relative_to(PROJECT_ROOT)
        artifact_key = filename.rsplit(".", 1)[0].replace("-", "_")
        rows.append((artifact_key, artifact_type, str(rel)))
    return rows

def values_sql(rows: list[tuple[str, ...]]) -> str:
    return ",\n".join("(" + ", ".join(sql_literal(v) for v in row) + ")" for row in rows)

def apply_sql(args: argparse.Namespace, route_data, artifact_rows, validation_statuses) -> str:
    route, fallback, status, now, later, forbidden, setup = route_data
    lk = sql_literal(args.launch_key)
    artifact_values = values_sql(artifact_rows)
    validation_values = ",\n".join(
        f"({sql_literal(k)}, {sql_literal(v)}, {sql_literal('Generated artifact validation: ' + k.replace('_', ' ') + '.')})"
        for k, v in validation_statuses.items()
    )
    steps = [
        ("operator_review_permission_route", 10, "operator", "needs_operator_action", "permission_review"),
        ("operator_connect_github_optional", 20, "operator", "needs_operator_action", "connect_github"),
        ("operator_enable_velo_optional", 30, "operator", "needs_operator_action", "install_wix_cli"),
        ("codex_review_generated_artifacts", 40, "codex", "ready_for_agent", "run_qa"),
        ("operator_add_custom_element_if_needed", 50, "operator", "planned", "add_custom_element"),
        ("operator_paste_or_sync_code", 60, "operator", "planned", "paste_code"),
        ("operator_preview_site", 70, "operator", "planned", "preview_site"),
        ("operator_report_build_status", 80, "operator", "planned", "run_qa"),
        ("staging_qa_later", 90, "operator", "planned", "run_qa"),
    ]
    step_values = ",\n".join(
        f"({sql_literal(k)}, {order}, {sql_literal(owner)}, {sql_literal(step_status)}, {sql_literal(step_type)}, {sql_literal('Phase 7.23 AI build step: ' + k.replace('_', ' ') + '.')})"
        for k, order, owner, step_status, step_type in steps
    )
    reviews = [
        ("execution_route_review", "high"),
        ("permission_route_review", "high"),
        ("code_artifact_review", "high"),
        ("custom_element_review", "normal"),
        ("velo_review", "normal"),
        ("form_review", "high"),
        ("seo_review", "normal"),
        ("safety_review", "blocker"),
        ("publish_blocker_review", "blocker"),
    ]
    review_values = ",\n".join(f"({sql_literal(rt)}, {sql_literal(pr)})" for rt, pr in reviews)
    return f"""
BEGIN;

DO $GUARD$
DECLARE live_count int; plans int; inbound_count int; contacts_count int; send_count int; publish_count int; sent_count int; active_keys int; fake_ready boolean; prod_ready boolean;
BEGIN
  SELECT count(*) INTO live_count
  FROM wix_staging_sites s JOIN launch_projects p ON p.id = s.launch_project_id
  WHERE p.launch_key = {lk}
    AND (s.real_domain_connected OR s.public_indexing_enabled OR s.page_published OR s.live_form_created
      OR s.live_webhook_created OR s.external_tracking_enabled OR s.wix_api_call_made);
  SELECT count(*) INTO plans
  FROM wix_ai_build_execution_plans e JOIN launch_projects p ON p.id = e.launch_project_id
  WHERE p.launch_key = {lk} AND e.raw_context->>'phase' = '{PHASE}' AND e.raw_context->>'source' = '{SOURCE}';
  SELECT count(*) INTO inbound_count FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  SELECT send_enabled_count, publish_enabled_count, communication_sent
    INTO send_count, publish_count, sent_count
  FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT count(*) INTO active_keys FROM wix_api_key_profiles WHERE profile_status = 'active' OR secret_value_stored OR external_call_allowed;
  SELECT ready_for_fake_lead_test INTO fake_ready FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk};
  SELECT ready_for_production_publish INTO prod_ready FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk};
  IF live_count <> 0 THEN RAISE EXCEPTION 'Refusing: staging site has live/domain/index/publish/form/webhook/tracking/api flag.'; END IF;
  IF plans <> 0 AND NOT {str(args.allow_existing).lower()}::boolean THEN RAISE EXCEPTION 'Refusing duplicate Phase 7.23 execution plan.'; END IF;
  IF inbound_count <> 0 THEN RAISE EXCEPTION 'Refusing: inbound leads count is %.', inbound_count; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 OR sent_count <> 0 THEN RAISE EXCEPTION 'Refusing: send/publish/communication count is nonzero.'; END IF;
  IF active_keys <> 0 THEN RAISE EXCEPTION 'Refusing: active/external/secret Wix API key profile exists.'; END IF;
  IF fake_ready OR prod_ready THEN RAISE EXCEPTION 'Refusing: fake lead or production publish readiness is true.'; END IF;
END $GUARD$;

WITH project AS (
  SELECT id FROM launch_projects WHERE launch_key = {lk}
),
site AS (
  SELECT s.*
  FROM wix_staging_sites s
  WHERE s.launch_project_id IN (SELECT id FROM project)
  ORDER BY s.created_at DESC
  LIMIT 1
),
plan_insert AS (
  INSERT INTO wix_ai_build_execution_plans
    (launch_project_id, wix_staging_site_id, execution_key, execution_status, preferred_route,
     fallback_route, requires_human_setup, requires_wix_api_key, requires_wix_cli,
     requires_github_connection, requires_custom_element, requires_code_paste, wix_api_call_made,
     external_call_made, publish_enabled, live_webhook_created, permission_analysis_summary,
     required_permissions_now, required_permissions_later, forbidden_permissions_now,
     recommended_key_profile_for_route, route_blockers, operator_setup_needed, safe_summary,
     operator_setup_instructions, raw_context)
  SELECT
    p.id, s.id, 'dlf_gallery_white_ai_build_v1', {sql_literal(status)}, {sql_literal(route)},
    {sql_literal(fallback)}, true, false,
    {str(route == 'wix_git_cli').lower()}::boolean,
    {str(route == 'wix_git_cli').lower()}::boolean,
    {str(route == 'wix_custom_element_velo').lower()}::boolean,
    {str(route == 'wix_code_snippet').lower()}::boolean,
    false, false, false, false,
    'Phase 7.21 permission map used. No key now; Git/CLI preferred, Custom Element/Velo fallback, snippets only if necessary. APIs later for CMS/forms/media/blog/FAQ/tags/analytics/automation.',
    {json_literal(now)}::jsonb,
    {json_literal(later)}::jsonb,
    {json_literal(forbidden)}::jsonb,
    'wix_staging_build_key_later',
    {json_literal(route_data[6])}::jsonb,
    {json_literal(setup)}::jsonb,
    'AI-executable staging build plan generated. No Wix API/key/publish/live webhook/tracking.',
    'Operator reviews route, then either connects Git/Wix CLI, enables Velo and adds one Custom Element, or uses snippet fallback. Preview only.',
    jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
  FROM project p CROSS JOIN site s
  RETURNING id, launch_project_id
),
artifact_input(artifact_key, artifact_type, artifact_path) AS (
  VALUES
  {artifact_values}
),
artifact_insert AS (
  INSERT INTO wix_ai_build_artifacts
    (execution_plan_id, launch_project_id, artifact_key, artifact_type, artifact_status, artifact_path,
     contains_private_contact_data, contains_secrets, contains_api_key, contains_live_webhook,
     publish_enabled, safe_summary, raw_context)
  SELECT pi.id, pi.launch_project_id, ai.artifact_key, ai.artifact_type, 'generated', ai.artifact_path,
         false, false, false, false, false,
         'Generated Phase 7.23 artifact; review before use in Wix staging.',
         jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
  FROM plan_insert pi CROSS JOIN artifact_input ai
  RETURNING id, execution_plan_id, launch_project_id, artifact_key
),
step_input(step_key, step_order, step_owner, step_status, step_type, safe_summary) AS (
  VALUES
  {step_values}
),
step_insert AS (
  INSERT INTO wix_ai_build_steps
    (execution_plan_id, launch_project_id, step_key, step_order, step_owner, step_status, step_type,
     safe_summary, operator_instruction, agent_instruction, raw_context)
  SELECT pi.id, pi.launch_project_id, si.step_key, si.step_order, si.step_owner, si.step_status, si.step_type,
         si.safe_summary, si.safe_summary, si.safe_summary,
         jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
  FROM plan_insert pi CROSS JOIN step_input si
  RETURNING id, execution_plan_id, launch_project_id, step_key
),
validation_input(validation_type, validation_status, safe_summary) AS (
  VALUES
  {validation_values}
),
validation_insert AS (
  INSERT INTO wix_ai_build_validation_results
    (execution_plan_id, artifact_id, validation_type, validation_status, safe_summary, raw_context)
  SELECT pi.id, NULL::uuid, vi.validation_type, vi.validation_status, vi.safe_summary,
         jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
  FROM plan_insert pi CROSS JOIN validation_input vi
  RETURNING id, execution_plan_id, validation_type
),
review_input(review_type, priority) AS (
  VALUES
  {review_values}
)
INSERT INTO wix_ai_build_review_items
  (launch_project_id, execution_plan_id, review_type, status, priority, raw_context)
SELECT pi.launch_project_id, pi.id, ri.review_type, 'pending', ri.priority,
       jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
FROM plan_insert pi CROSS JOIN review_input ri;

COMMIT;

SELECT 'execution_plans', execution_status || '|' || preferred_route || '|' || count(*) FROM wix_ai_build_execution_plans e JOIN launch_projects p ON p.id = e.launch_project_id WHERE p.launch_key = {lk} GROUP BY execution_status, preferred_route
UNION ALL SELECT 'artifacts', artifact_type || '|' || artifact_status || '|' || count(*) FROM wix_ai_build_artifacts a JOIN launch_projects p ON p.id = a.launch_project_id WHERE p.launch_key = {lk} GROUP BY artifact_type, artifact_status
UNION ALL SELECT 'steps', step_type || '|' || step_status || '|' || step_owner || '|' || count(*) FROM wix_ai_build_steps s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk} GROUP BY step_type, step_status, step_owner
UNION ALL SELECT 'validations', validation_type || '|' || validation_status || '|' || count(*) FROM wix_ai_build_validation_results v JOIN wix_ai_build_execution_plans e ON e.id = v.execution_plan_id JOIN launch_projects p ON p.id = e.launch_project_id WHERE p.launch_key = {lk} GROUP BY validation_type, validation_status
UNION ALL SELECT 'review_items', review_type || '|' || status || '|' || count(*) FROM wix_ai_build_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} GROUP BY review_type, status
UNION ALL SELECT 'ready_for_code_review', ready_for_code_review::text FROM vw_dlf_wix_ai_build_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_operator_setup', ready_for_operator_setup::text FROM vw_dlf_wix_ai_build_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_wix_implementation', ready_for_wix_implementation::text FROM vw_dlf_wix_ai_build_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_fake_lead_test', ready_for_fake_lead_test::text FROM vw_dlf_wix_ai_build_readiness WHERE launch_key = {lk}
ORDER BY 1, 2;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Create Phase 7.23 DLF Wix AI build execution plan. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--output-dir", default="exports/wix_ai_builds")
    parser.add_argument("--preferred-route", choices=ALLOWED_ROUTES, default="auto")
    parser.add_argument("--allow-existing", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Wix AI build plan. launch_key={args.launch_key}. Counts only; staging URL hidden.")
    if not args.real_ok:
        print("Refusing: --real-ok is required, even for dry-run.")
        return 1

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 13:
        print("Refusing: probe returned no usable result.")
        return 1
    project_count, site_count, live_flags, existing, perm_rows, active_keys, inbound, contacts, send, publish, sent, fake_ready, prod_ready = fields[:13]
    print("baseline:")
    labels = (
        "launch_projects", "staging_sites", "staging_live_flags", "existing_phase_7_23_plans",
        "permission_catalog_rows", "active_or_secret_key_profiles", "inbound_leads", "contacts",
        "send_enabled", "publish_enabled", "communication_sent", "ready_for_fake_lead_test",
        "ready_for_production_publish",
    )
    for label, value in zip(labels, fields[:13]):
        print(f"  {label}: {value}")
    if project_count != "1":
        print("Refusing: launch project missing or ambiguous.")
        return 1
    if site_count == "0":
        print("Refusing: no Wix staging site exists.")
        return 1
    if live_flags != "0":
        print("Refusing: staging site has a live/domain/index/publish/form/webhook/tracking/api flag.")
        return 1
    if existing != "0" and not args.allow_existing:
        print("Refusing: duplicate Phase 7.23 execution plan exists. Use --allow-existing only for intentional reruns.")
        return 1
    if active_keys != "0" or inbound != "0" or contacts != "4" or send != "0" or publish != "0" or sent != "0":
        print("Refusing: key/lead/contact/send/publish safety baseline is not clean.")
        return 1
    if fake_ready != "false" or prod_ready != "false":
        print("Refusing: fake lead or production publish readiness is true.")
        return 1

    code, perms = run_psql(permission_summary_sql())
    if code != 0:
        print(perms)
        return code
    print("permission_map_summary:")
    for line in perms.splitlines():
        print(f"  {line}")

    route_data = choose_route(args.preferred_route)
    route = route_data[0]
    artifacts = artifact_texts(route)
    validation_statuses = validate_artifacts(artifacts)
    artifact_rows = write_artifacts((PROJECT_ROOT / args.output_dir).resolve(), artifacts, args.apply)
    print("projected:")
    print(f"  preferred_route: {route}")
    print(f"  fallback_route: {route_data[1]}")
    print(f"  execution_status: {route_data[2]}")
    print(f"  artifacts: {len(artifact_rows)}")
    print(f"  validations: {len(validation_statuses)} total; failures: {sum(1 for v in validation_statuses.values() if v == 'failed')}")
    print("  wix_api_calls: 0   api_keys_read_or_stored: 0   publish/live_webhook/tracking: 0")

    if any(v == "failed" for v in validation_statuses.values()):
        print("Refusing: generated artifact validation failed.")
        for key, value in validation_statuses.items():
            if value == "failed":
                print(f"  failed_validation: {key}")
        return 1

    if not args.apply:
        print("Dry run only. No files or database rows were written.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args, route_data, artifact_rows, validation_statuses))
    print("Apply result:" if code == 0 else "Apply FAILED:")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
