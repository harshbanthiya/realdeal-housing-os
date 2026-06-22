#!/usr/bin/env python3
"""Phase 7.19 — seed the DLF Westpark Wix staging / preview-site plan. Dry-run by default.

Creates one planned Wix staging-site record, a Gallery White build checklist, pre-publish QA
checks, and a human review queue so the website can be built and tested visually WITHOUT
connecting the real domain, publishing production pages, enabling public indexing, wiring live
forms/webhooks, enabling external tracking, or creating real leads.

It performs NO Wix API call, NO n8n call, NO external API call, NO publishing, NO live
form/webhook, NO sends, and NO inbound-lead/contact writes. Every staging-site live flag stays
false. Writing requires BOTH --real-ok and --apply. Counts only; never prints contact values.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.19"
SOURCE = "dlf_wix_staging_site_plan_seed"
STAGING_KEY = "dlf-westpark-gallery-white-staging"
STAGING_NAME = "DLF Westpark Gallery White Staging"
STAGING_SUMMARY = (
    "Manually-created Wix staging/preview site for the approved Gallery White design. "
    "No real domain, no public indexing, no published pages, no live forms/webhooks, no "
    "external tracking, no Wix API calls — build and visual QA only."
)

# (checklist_key, checklist_category, priority, safe_summary)
CHECKLIST_ITEMS = [
    ("staging-setup", "setup", "high",
     "Create a NEW Wix site (or duplicate) as a separate staging/preview project — never the live site."),
    ("no-domain-connected", "safety", "blocker",
     "Do NOT connect the real domain; keep the free *.wixsite.com staging URL only."),
    ("no-public-indexing", "safety", "blocker",
     "Keep the staging site hidden from search engines (noindex / not discoverable)."),
    ("homepage-landing-shell", "setup", "high",
     "Lay out the homepage + project-landing page shells per the Gallery White page architecture."),
    ("gallery-white-hero", "hero", "high",
     "Type-first hero with a slice of the hero image revealed above the fold (accepted refinement)."),
    ("section-01-project", "content_sections", "normal",
     "Section 01 The project: H2 + short paragraph + three-stat hairline row (placeholders until verified)."),
    ("section-02-location", "content_sections", "normal",
     "Section 02 Location: proximity ledger + static multi-state map card (no live embed)."),
    ("section-03-lifestyle", "content_sections", "normal",
     "Section 03 Lifestyle: asymmetric image pair with wipe reveals; placeholder frames until photography."),
    ("section-04-residences", "content_sections", "normal",
     "Section 04 Residences: mist-band ledger rows; carpet/price as monospace placeholder tokens."),
    ("section-05-perspective", "content_sections", "normal",
     "Section 05 Perspective: asymmetric numeral + editorial statement (no-guaranteed-returns voice)."),
    ("section-06-verified-facts", "content_sections", "normal",
     "Section 06 Verified facts: check-icon rows; values resolve placeholder -> real over time."),
    ("section-07-enquiry-form", "form", "high",
     "Section 07 Enquiry: Wix Form to MANUAL review only — no live webhook, no live submission routing."),
    ("faq-section", "content_sections", "normal",
     "FAQ as native collapsible disclosures; schema markup deferred until facts are verified."),
    ("footer", "content_sections", "normal",
     "Footer: facet signature strip + copyright / RERA placeholder token / internal links."),
    ("sticky-cta", "navigation", "normal",
     "Sticky CTA: desktop WhatsApp pill / mobile two-segment bar; intersection-hide before the form."),
    ("mobile-layout", "mobile", "high",
     "Mobile layout: stacked sections, >=16px inputs, 44px+ targets, scroll-reveal section nav."),
    ("consent-fields", "consent", "high",
     "Consent: granular unchecked checkboxes + privacy/opt-out copy beside submit; never pre-ticked."),
    ("utm-hidden-fields", "tracking", "normal",
     "Add hidden UTM capture fields on the form for later attribution (no live tracking pixel fires)."),
    ("factual-placeholders", "placeholders", "high",
     "Keep RERA/price/brochure/visual placeholders verbatim or as branded 'pending' copy — no invented values."),
    ("performance-image-aspect-ratios", "performance", "high",
     "Set explicit aspect ratios on every image container to keep CLS near zero (accepted refinement)."),
]

# (qa_key, qa_type, blocker, safe_summary)
QA_CHECKS = [
    ("qa-no-real-domain", "domain_not_connected", True,
     "Confirm the staging site is on the *.wixsite.com URL and the real domain is NOT connected."),
    ("qa-no-public-indexing", "noindex", True,
     "Confirm the staging site is not publicly indexable (noindex / hidden from search)."),
    ("qa-no-live-webhook", "webhook_disabled", True,
     "Confirm no live webhook / automation is wired from the form."),
    ("qa-no-live-tracking", "tracking_disabled", True,
     "Confirm no analytics/ads pixel (GA4/GTM/Meta) is firing on the staging site."),
    ("qa-no-publish", "noindex", True,
     "Confirm no production page is published to the live domain from this staging work."),
    ("qa-mobile-layout", "mobile_layout", True,
     "Mobile layout renders correctly: stacking, tap targets, sticky bar, no overflow."),
    ("qa-desktop-layout", "desktop_layout", False,
     "Desktop layout matches the Gallery White spec: spacing, hierarchy, dark anchors."),
    ("qa-form-fields", "form_fields", True,
     "Form fields present and correct; submissions route to manual review only."),
    ("qa-consent-fields", "consent_fields", True,
     "Consent checkboxes present, unchecked by default, with privacy/opt-out copy."),
    ("qa-placeholder-integrity", "placeholder_integrity", True,
     "All unverified facts still show placeholders / branded pending copy — no fabricated values."),
    ("qa-seo-metadata", "seo_metadata", False,
     "Titles/meta/H1-H2 follow the spec; SEO text is in the DOM, never in canvas."),
    ("qa-accessibility", "accessibility", False,
     "Contrast, focus rings, programmatic labels, one H1 per page."),
    ("qa-performance", "performance", False,
     "Image aspect ratios fixed; LCP/CLS within budget on the staging preview."),
]

# (review_type, priority)
REVIEW_ITEMS = [
    ("staging_setup_review", "high"),
    ("build_checklist_review", "normal"),
    ("qa_review", "high"),
    ("safety_review", "blocker"),
    ("noindex_review", "blocker"),
    ("domain_review", "blocker"),
    ("publish_blocker_review", "blocker"),
]
def project_exists(launch_key: str) -> bool:
    code, output = run_psql(f"SELECT count(*) FROM launch_projects WHERE launch_key = {sql_literal(launch_key)};")
    return code == 0 and output.strip() == "1"

def existing_count(launch_key: str) -> int:
    code, output = run_psql(f"""
SELECT count(*) FROM wix_staging_sites s JOIN launch_projects p ON p.id = s.launch_project_id
WHERE p.launch_key = {sql_literal(launch_key)}
  AND s.raw_context->>'phase' = '{PHASE}' AND s.raw_context->>'source' = '{SOURCE}';
""")
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
        "'wix_api_call_made'", "false",
        "'publish_enabled'", "false",
        "'communication_sent'", "false",
    ]
    if extra:
        for k, v in extra.items():
            pairs.append(sql_literal(k))
            pairs.append(sql_literal(v))
    return "jsonb_build_object(" + ", ".join(pairs) + ")"

def apply_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    checklist_rows = ",\n      ".join(
        "(" + ", ".join([sql_literal(k), sql_literal(cat), sql_literal(pri), sql_literal(summary)]) + ")"
        for k, cat, pri, summary in CHECKLIST_ITEMS
    )
    qa_rows = ",\n      ".join(
        "(" + ", ".join([sql_literal(k), sql_literal(t), sql_literal(b), sql_literal(summary)]) + ")"
        for k, t, b, summary in QA_CHECKS
    )
    review_rows = ",\n      ".join(
        "(" + ", ".join([sql_literal(rt), sql_literal(pri)]) + ")"
        for rt, pri in REVIEW_ITEMS
    )

    return f"""
BEGIN;

DELETE FROM wix_staging_review_items ri
USING launch_projects p
WHERE ri.launch_project_id = p.id AND p.launch_key = {lk}
  AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}';
DELETE FROM wix_staging_qa_checks q
USING launch_projects p
WHERE q.launch_project_id = p.id AND p.launch_key = {lk}
  AND q.raw_context->>'phase' = '{PHASE}' AND q.raw_context->>'source' = '{SOURCE}';
DELETE FROM wix_staging_build_checklist_items c
USING launch_projects p
WHERE c.launch_project_id = p.id AND p.launch_key = {lk}
  AND c.raw_context->>'phase' = '{PHASE}' AND c.raw_context->>'source' = '{SOURCE}';
DELETE FROM wix_staging_sites s
USING launch_projects p
WHERE s.launch_project_id = p.id AND p.launch_key = {lk}
  AND s.raw_context->>'phase' = '{PHASE}' AND s.raw_context->>'source' = '{SOURCE}';

WITH project AS (
  SELECT id FROM launch_projects WHERE launch_key = {lk}
),
site AS (
  INSERT INTO wix_staging_sites
    (launch_project_id, staging_key, staging_status, staging_site_name, staging_site_url,
     real_domain_connected, public_indexing_enabled, wix_api_call_made, page_created,
     page_published, live_form_created, live_webhook_created, external_tracking_enabled,
     human_review_required, safe_summary, raw_context)
  SELECT p.id, {sql_literal(STAGING_KEY)}, 'planned', {sql_literal(STAGING_NAME)}, NULL,
     false, false, false, false, false, false, false, false, true,
     {sql_literal(STAGING_SUMMARY)}, {ctx()}
  FROM project p
  RETURNING id, launch_project_id
),
checklist AS (
  INSERT INTO wix_staging_build_checklist_items
    (launch_project_id, wix_staging_site_id, checklist_key, checklist_category, checklist_status,
     priority, safe_summary, raw_context)
  SELECT site.launch_project_id, site.id, v.checklist_key, v.checklist_category, 'pending',
     v.priority, v.safe_summary, {ctx()}
  FROM site
  JOIN (VALUES
      {checklist_rows}
  ) AS v(checklist_key, checklist_category, priority, safe_summary) ON true
  RETURNING id
),
qa AS (
  INSERT INTO wix_staging_qa_checks
    (launch_project_id, wix_staging_site_id, qa_key, qa_type, qa_status, blocker, safe_summary, raw_context)
  SELECT site.launch_project_id, site.id, v.qa_key, v.qa_type, 'pending', v.blocker, v.safe_summary, {ctx()}
  FROM site
  JOIN (VALUES
      {qa_rows}
  ) AS v(qa_key, qa_type, blocker, safe_summary) ON true
  RETURNING id
)
INSERT INTO wix_staging_review_items
  (launch_project_id, wix_staging_site_id, review_type, status, priority, raw_context)
SELECT site.launch_project_id, site.id, v.review_type, 'pending', v.priority, {ctx()}
FROM site
JOIN (VALUES
    {review_rows}
) AS v(review_type, priority) ON true;

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
  IF bad > 0 THEN RAISE EXCEPTION 'Refusing: a staging site has a live/domain/indexing/publish/api flag set.'; END IF;
  IF inbound <> 0 THEN RAISE EXCEPTION 'Refusing: inbound lead count changed to %.', inbound; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
  IF se > 0 OR pe > 0 THEN RAISE EXCEPTION 'Refusing: send/publish enabled (send=%, publish=%).', se, pe; END IF;
END $GUARD$;

COMMIT;

SELECT 'staging_sites', count(*)::text FROM wix_staging_sites s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk} AND s.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'checklist_items', count(*)::text FROM wix_staging_build_checklist_items c JOIN launch_projects p ON p.id = c.launch_project_id WHERE p.launch_key = {lk} AND c.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'qa_checks', count(*)::text FROM wix_staging_qa_checks q JOIN launch_projects p ON p.id = q.launch_project_id WHERE p.launch_key = {lk} AND q.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'review_items', count(*)::text FROM wix_staging_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'real_domain_connected_count', real_domain_connected_count::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'public_indexing_enabled_count', public_indexing_enabled_count::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'page_published_count', page_published_count::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'live_form_created_count', live_form_created_count::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'live_webhook_created_count', live_webhook_created_count::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_manual_staging_build', ready_for_manual_staging_build::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_staging_qa', ready_for_staging_qa::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_production_publish', ready_for_production_publish::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}
ORDER BY 1;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Seed DLF Westpark Wix staging-site plan. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--allow-existing", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Westpark Wix staging-site plan seed. launch_key={args.launch_key}. Counts only; no contact values.")

    if not project_exists(args.launch_key):
        print(f"Refusing: launch project '{args.launch_key}' not found.")
        return 1

    existing = existing_count(args.launch_key)
    if existing < 0:
        print("Refusing: could not probe existing staging rows.")
        return 1
    if existing > 0 and not args.allow_existing:
        print(f"Refusing: {existing} Phase 7.19 staging site(s) already exist. Re-run with --allow-existing to replace.")
        return 1

    print("projected:")
    print("  staging sites: 1 (planned)")
    print(f"  build checklist items: {len(CHECKLIST_ITEMS)}")
    print(f"  QA checks: {len(QA_CHECKS)}")
    print(f"  review items: {len(REVIEW_ITEMS)}")
    print("  real_domain_connected: false   public_indexing_enabled: false   wix_api_call_made: false")
    print("  page_created/page_published: false   live_form_created/live_webhook_created: false   external_tracking_enabled: false")
    print("  Wix/n8n/Meta/WhatsApp/email API calls: 0   publishing: 0   live forms/webhooks: 0")
    print("  inbound_leads_created: 0   contacts_created_or_merged: 0   messages_sent: 0")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(apply_sql(args.launch_key))
    print("Staging-site plan seeded:" if code == 0 else "Seed FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
