#!/usr/bin/env python3
"""Phase 7.16 — create a privacy-safe Fable UI/UX handoff package for DLF Westpark.

Distills the approved Phase 7.15 Wix UX/SEO/integration masterplan into two local
Markdown artifacts a human can paste into Fable: a concise prompt and a detailed
design brief. It performs NO Fable call, NO external API call, NO publishing, NO
live form/webhook, NO sends, and NO inbound-lead/contact writes.

Artifacts contain ONLY public/business-safe design direction: no contact names,
phones, emails, raw lead/contact data, secrets, DB IDs, or internal source paths.
Unverified facts stay as placeholders. Dry-run by default; writing the artifacts +
DB rows requires BOTH --real-ok and --apply. Artifacts are written under the
git-ignored exports/fable_handoffs/ directory only. Counts only, plus paths.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
import hashlib
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.16"
SOURCE = "dlf_fable_uiux_handoff_package"
PACKAGE_KEY = "dlf-westpark-fable-uiux-handoff"
BLUEPRINT_KEY = "dlf-westpark-wix-experience"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "exports" / "fable_handoffs"
CONCISE_NAME = "dlf-westpark-fable-prompt-concise.md"
DETAILED_NAME = "dlf-westpark-fable-design-brief.md"

FACTUAL_PLACEHOLDERS = (
    "RERA_VERIFY",
    "PRICE_VERIFY",
    "BROCHURE_LINK_PENDING",
    "WIX_PAGE_PENDING",
    "VERIFY",
    "VISUAL_DIRECTION_PENDING",
)

FORBIDDEN_PHRASES = (
    "guaranteed return", "guaranteed returns", "assured return",
    "limited time only", "hurry", "last few units", "only a few left",
    "selling fast", "book before price rises",
)
NEGATIONS = ("no", "not", "without", "never", "zero")

# Section definitions: (section_key, section_type, in_concise, safe_summary).
SECTIONS = [
    ("brand-direction", "brand_direction", True,
     "Apple-inspired (not copied) luxury real estate brand: clean, premium, minimal, calm, trustworthy."),
    ("target-audience", "target_audience", True,
     "Andheri West / western-suburbs luxury buyers, NRI/investor buyers, channel partners."),
    ("page-architecture", "page_architecture", True,
     "Seven pages: homepage, project landing, area SEO, building SEO, blog hub, thank-you, privacy."),
    ("landing-page-flow", "landing_page_flow", True,
     "Hero-first scroll narrative: identity -> location -> lifestyle -> configuration -> investment -> verified facts -> lead form."),
    ("visual-language", "visual_language", True,
     "Neutral black/white/stone/charcoal + restrained gold accent; premium sans-serif; large whitespace; image-first."),
    ("motion-language", "motion_language", True,
     "Subtle scroll reveals, sticky CTA behavior, smooth section transitions; no heavy animation."),
    ("conversion-goals", "conversion_goals", True,
     "Premium lead form, sticky WhatsApp CTA on mobile, brochure/price/site-visit intent, thank-you next action."),
    ("seo-constraints", "seo_constraints", True,
     "Clean H1/H2 hierarchy, SEO FAQ, internal links; never hide important text inside canvas; speed is a blocker."),
    ("component-requirements", "component_requirements", False,
     "Hero, lead form, sticky WhatsApp CTA, trust bar, SEO FAQ, location/lifestyle, blog grid, thank-you tracker, mobile bottom CTA."),
    ("threejs-guidance", "threejs_guidance", True,
     "Optional lightweight WebGL hero accent only; progressive enhancement; static fallback; must not block LCP or hurt mobile/SEO."),
    ("wix-constraints", "wix_constraints", True,
     "Must be buildable in Wix; no live forms/webhooks now; respect Wix layout/section model."),
    ("placeholder-rules", "placeholder_rules", True,
     "Keep unverified facts as placeholders (RERA/price/brochure/visual); no false scarcity or guaranteed-return claims."),
]

VALIDATIONS = (
    "no_contact_data",
    "no_secrets",
    "no_internal_db_ids",
    "placeholders_preserved",
    "apple_inspired_not_copied",
    "mobile_first",
    "seo_constraints_present",
    "wix_constraints_present",
    "fable_token_efficiency",
)

REVIEWS = (
    ("fable_prompt_review", "high"),
    ("design_direction_review", "high"),
    ("privacy_review", "blocker"),
    ("seo_review", "normal"),
    ("conversion_review", "high"),
    ("wix_feasibility_review", "normal"),
    ("threejs_review", "normal"),
)

# Concise prompt token-efficiency budget (characters).
CONCISE_CHAR_BUDGET = 4500
def fetch_strategy(launch_key: str) -> dict | None:
    """Pull the approved Phase 7.15 design strategy (public design content only).

    Returns blueprint design text, page architecture, and key design components.
    No contact rows, no DB ids are surfaced into artifacts (ids stay server-side).
    """
    lk = sql_literal(launch_key)
    sql = f"""
SELECT json_build_object(
  'display_name', COALESCE(p.project_display_name, 'DLF Westpark'),
  'blueprint', (
    SELECT to_json(b) FROM (
      SELECT design_direction, premium_visual_strategy, threejs_component_strategy,
             seo_strategy_summary, target_audience, primary_conversion_goals, site_goal
      FROM wix_site_experience_blueprints
      WHERE launch_project_id = p.id AND blueprint_key = {sql_literal(BLUEPRINT_KEY)}
      ORDER BY created_at LIMIT 1
    ) b
  ),
  'pages', (
    SELECT COALESCE(json_agg(pg ORDER BY pg.page_type), '[]'::json) FROM (
      SELECT page_type, page_goal, seo_intent, target_keyword, suggested_slug, primary_cta
      FROM wix_page_blueprints WHERE launch_project_id = p.id
    ) pg
  ),
  'components', (
    SELECT COALESCE(json_agg(c ORDER BY c.component_key), '[]'::json) FROM (
      SELECT component_key, component_type, design_goal, performance_risk, seo_risk
      FROM wix_design_component_specs WHERE launch_project_id = p.id
    ) c
  )
)
FROM launch_projects p
WHERE p.launch_key = {lk};
"""
    code, output = run_psql(sql)
    if code != 0 or not output.strip():
        return None
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return None
    if not data.get("blueprint"):
        return None
    return data

def build_concise_prompt(strategy: dict) -> str:
    name = strategy.get("display_name") or "DLF Westpark"
    pages = strategy.get("pages") or []
    page_list = ", ".join(sorted({pg.get("page_type", "") for pg in pages if pg.get("page_type")}))
    lines = [
        f"# Fable Prompt — {name} Website (Real Deal Housing)",
        "",
        "Design a premium, mobile-first luxury real estate website UI/UX. Apple-inspired, NOT copied.",
        "",
        "Brand feel: clean, premium, minimal, calm, trustworthy, technically polished. Neutral palette —",
        "black / white / stone / charcoal with a restrained gold accent. Large whitespace, premium",
        "sans-serif typography (large headlines, restrained body, generous line-height, few weights),",
        "strong visual hierarchy, cinematic property imagery, image-first layouts. No broker-portal",
        "clutter, no loud colors, no overstuffed cards, no cheap real-estate template look.",
        "",
        f"Pages to design: {page_list}.",
        "",
        "Landing page = hero-first scroll storytelling, one idea per section:",
        "project identity → location advantage → lifestyle → configuration interest →",
        "investment/referral angle → verified facts → lead form.",
        "",
        "Hero: full-width cinematic hero, one short headline, one primary CTA, one secondary CTA,",
        "quiet trust markers. Motion: subtle scroll reveals, sticky CTA behavior, smooth transitions.",
        "Optional Three.js/WebGL only as a lightweight hero accent with a static image fallback —",
        "must not block load speed, hurt mobile UX, or hide SEO text inside a canvas.",
        "",
        "Conversion: premium (not spammy) lead form with visible privacy/consent + opt-out near submit;",
        "sticky click-to-WhatsApp CTA that becomes a mobile bottom bar; brochure / price / site-visit",
        "intent capture; a thank-you page designed for the next action.",
        "",
        "SEO: clean H1/H2 hierarchy, an SEO FAQ section, internal links to area/building/blog pages;",
        "important copy stays in real DOM text (never inside canvas); mobile performance is a hard",
        "requirement. Must be buildable in Wix.",
        "",
        "Keep these placeholders verbatim wherever a fact is not yet verified — do NOT invent values:",
        "RERA_VERIFY, PRICE_VERIFY, BROCHURE_LINK_PENDING, WIX_PAGE_PENDING, VERIFY,",
        "VISUAL_DIRECTION_PENDING. Never use false scarcity or guaranteed-return language.",
        "",
        "Deliver: layout, section flow, typography scale, color usage, component styling, and mobile",
        "behavior for the pages above. Design only — no backend, no live integrations.",
    ]
    return "\n".join(lines) + "\n"

def build_detailed_brief(strategy: dict) -> str:
    name = strategy.get("display_name") or "DLF Westpark"
    b = strategy.get("blueprint") or {}
    pages = strategy.get("pages") or []
    components = strategy.get("components") or []
    audience = b.get("target_audience") or []
    goals = b.get("primary_conversion_goals") or []

    lines = [
        f"# Fable Design Brief — {name} Website (Real Deal Housing)",
        "",
        "> Designer-facing brief. Public/business-safe only — no contacts, no raw data, no secrets, no",
        "> DB identifiers. Paste into Fable for UI/UX design only. No backend or live integration work.",
        "",
        "## 1. Project & context",
        f"- Project: {name} (confirmed public name).",
        f"- Site goal: {b.get('site_goal') or '[VERIFY]'}",
        "- This is the Real Deal Housing website experience, leading with the DLF Westpark launch and",
        "  built to extend to future building-launch campaigns.",
        "",
        "## 2. Brand & design direction (Apple-inspired, not copied)",
        f"{b.get('design_direction') or '[VERIFY]'}",
        "",
        "## 3. Target audience",
    ]
    lines += [f"- {a}" for a in audience] or ["- [VERIFY]"]
    lines += [
        "",
        "## 4. Page architecture",
    ]
    for pg in pages:
        kw = pg.get("target_keyword") or "—"
        lines.append(
            f"- **{pg.get('page_type')}** (`{pg.get('suggested_slug', '')}`): {pg.get('page_goal', '')} "
            f"[SEO intent: {pg.get('seo_intent', '—')}; target keyword: {kw}; CTA: {pg.get('primary_cta', '—')}]"
        )
    lines += [
        "",
        "## 5. Landing page flow (hero-first scroll narrative)",
        "Each scroll section reveals ONE idea — do not dump all details at once:",
        "1. Project identity",
        "2. Location advantage",
        "3. Lifestyle",
        "4. Configuration interest",
        "5. Investment / referral angle",
        "6. Verified facts (placeholders until verified)",
        "7. Lead form",
        "",
        "## 6. Visual & typography language",
        f"{b.get('premium_visual_strategy') or '[VERIFY]'}",
        "- Palette: black / white / stone / charcoal with a restrained gold accent; soft contrast.",
        "- Typography: premium sans-serif, large headlines, restrained body, generous line-height, few weights.",
        "",
        "## 7. Motion language",
        "- Subtle scroll reveals, sticky CTA behavior, smooth section transitions.",
        "- No heavy animation that harms speed, mobile UX, or SEO; respect reduced-motion.",
        "",
        "## 8. Three.js / custom visual guidance",
        f"{b.get('threejs_component_strategy') or '[VERIFY]'}",
        "",
        "## 9. Conversion goals & form/consent UX",
    ]
    lines += [f"- Goal: {g}" for g in goals] or ["- [VERIFY]"]
    lines += [
        "- Lead form: premium and editorial (not spammy); minimal fields; brochure / price / site-visit",
        "  intent capture; privacy + consent + opt-out language visible near the submit button.",
        "- Sticky click-to-WhatsApp CTA that becomes a mobile bottom bar (consent-based).",
        "- Thank-you page designed for the next action.",
        "",
        "## 10. SEO constraints",
        f"{b.get('seo_strategy_summary') or '[VERIFY]'}",
        "- Clean H1/H2 hierarchy; SEO FAQ section; internal links to area/building/blog pages.",
        "- Important text stays in real DOM — never hidden inside a canvas/Three.js layer.",
        "- Mobile performance / Core Web Vitals are publish blockers.",
        "",
        "## 11. Component requirements",
    ]
    for c in components:
        lines.append(
            f"- **{c.get('component_type')}** (`{c.get('component_key')}`): {c.get('design_goal', '')} "
            f"[perf risk: {c.get('performance_risk', '—')}; SEO risk: {c.get('seo_risk', '—')}]"
        )
    lines += [
        "",
        "## 12. Wix constraints",
        "- The design must be buildable in Wix using its section/layout model.",
        "- No live forms or webhooks are wired in this phase; form submissions route to manual review.",
        "",
        "## 13. Placeholder rules (do not invent facts)",
        "Keep these verbatim wherever a fact is not yet verified:",
    ]
    lines += [f"- {ph}" for ph in FACTUAL_PLACEHOLDERS]
    lines += [
        "- Never use false scarcity or guaranteed-return language.",
        "",
        "## 14. Scope",
        "- UI/UX design only. No backend, no live Meta/WhatsApp/email/n8n/Wix integration, no publishing.",
        "",
    ]
    return "\n".join(lines) + "\n"

def _forbidden_affirmative_present(lower: str) -> bool:
    for phrase in FORBIDDEN_PHRASES:
        for match in re.finditer(re.escape(phrase), lower):
            prefix = lower[max(0, match.start() - 24):match.start()]
            preceding = re.findall(r"[a-z]+", prefix)
            if preceding and preceding[-1] in NEGATIONS:
                continue
            return True
    return False

def _secret_token_present(lower: str) -> bool:
    """True only for un-negated secret tokens.

    Prose assurances like "no secrets" / "no raw data" are negated and ignored;
    a real credential token (api_key=..., bearer ...) is not preceded by a negation.
    """
    for tok in ("password", "api_key", "apikey", "secret", "access_token", "bearer "):
        for match in re.finditer(re.escape(tok), lower):
            prefix = lower[max(0, match.start() - 20):match.start()]
            preceding = re.findall(r"[a-z]+", prefix)
            if preceding and preceding[-1] in NEGATIONS:
                continue
            return True
    return False

def validate_artifacts(concise: str, detailed: str) -> dict[str, str]:
    combined = concise + "\n" + detailed
    lower = combined.lower()
    has_email = bool(re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", lower))
    has_phone = bool(re.search(r"(?<!\w)(?:\+?91[\s-]?)?\d{10}(?!\w)", combined))
    has_secret = _secret_token_present(lower)
    has_uuid = bool(re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", lower))
    placeholders_present = all(ph in combined for ph in FACTUAL_PLACEHOLDERS)
    forbidden_present = _forbidden_affirmative_present(lower)
    return {
        "no_contact_data": "passed" if not (has_email or has_phone) else "failed",
        "no_secrets": "passed" if not has_secret else "failed",
        "no_internal_db_ids": "passed" if not has_uuid else "failed",
        "placeholders_preserved": "passed" if placeholders_present and not forbidden_present else "failed",
        "apple_inspired_not_copied": "passed" if ("apple-inspired" in lower and "not copied" in lower) else "failed",
        "mobile_first": "passed" if "mobile-first" in lower else "failed",
        "seo_constraints_present": "passed" if ("seo faq" in lower and ("h1/h2" in lower or "h2 hierarchy" in lower) and "canvas" in lower) else "failed",
        "wix_constraints_present": "passed" if "buildable in wix" in lower else "failed",
        "fable_token_efficiency": "passed" if len(concise) <= CONCISE_CHAR_BUDGET else "failed",
    }

def artifact_paths(output_dir: str) -> tuple[Path, Path]:
    out = Path(output_dir)
    if not out.is_absolute():
        out = PROJECT_ROOT / out
    return out / CONCISE_NAME, out / DETAILED_NAME

def apply_sql(launch_key: str, concise_path: Path, detailed_path: Path,
              digest: str, checks: dict[str, str]) -> str:
    lk = sql_literal(launch_key)

    def rel(path: Path) -> str:
        return str(path.relative_to(PROJECT_ROOT)) if path.is_relative_to(PROJECT_ROOT) else str(path)

    section_rows = ", ".join(
        f"({sql_literal(skey)}, {sql_literal(stype)}, {('true' if concise else 'false')}, {sql_literal(summary)})"
        for skey, stype, concise, summary in SECTIONS
    )
    validation_rows = ", ".join(
        f"({sql_literal(v)}, {sql_literal(checks[v])}, {sql_literal(v + ' -> ' + checks[v])})"
        for v in VALIDATIONS
    )
    review_rows = ", ".join(f"({sql_literal(rt)}, {sql_literal(pri)})" for rt, pri in REVIEWS)

    return f"""
BEGIN;

DO $GUARD$
DECLARE unsafe int; approved int;
BEGIN
  SELECT count(*) INTO unsafe
  FROM fable_uiux_handoff_packages hp JOIN launch_projects p ON p.id = hp.launch_project_id
  WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}'
    AND hp.raw_context->>'source' = '{SOURCE}'
    AND (hp.fable_call_made OR hp.external_call_made
         OR hp.contains_private_contact_data OR hp.contains_secrets);
  SELECT count(*) INTO approved
  FROM fable_uiux_handoff_packages hp JOIN launch_projects p ON p.id = hp.launch_project_id
  WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}'
    AND hp.raw_context->>'source' = '{SOURCE}'
    AND hp.package_status IN ('approved_for_fable', 'used_in_fable');
  IF unsafe > 0 THEN RAISE EXCEPTION 'Refusing: existing Phase 7.16 package marked called/external/contact/secret.'; END IF;
  IF approved > 0 THEN RAISE EXCEPTION 'Refusing: existing Phase 7.16 package already approved/used in Fable.'; END IF;
END $GUARD$;

DELETE FROM fable_uiux_handoff_review_items ri
USING fable_uiux_handoff_packages hp, launch_projects p
WHERE ri.handoff_package_id = hp.id AND hp.launch_project_id = p.id AND p.launch_key = {lk}
  AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}';
DELETE FROM fable_uiux_handoff_validation_results vr
USING fable_uiux_handoff_packages hp, launch_projects p
WHERE vr.handoff_package_id = hp.id AND hp.launch_project_id = p.id AND p.launch_key = {lk}
  AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}';
DELETE FROM fable_uiux_handoff_sections s
USING fable_uiux_handoff_packages hp, launch_projects p
WHERE s.handoff_package_id = hp.id AND hp.launch_project_id = p.id AND p.launch_key = {lk}
  AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}';
DELETE FROM fable_uiux_handoff_packages hp
USING launch_projects p
WHERE hp.launch_project_id = p.id AND p.launch_key = {lk}
  AND hp.raw_context->>'phase' = '{PHASE}' AND hp.raw_context->>'source' = '{SOURCE}';

WITH project AS (
  SELECT id FROM launch_projects WHERE launch_key = {lk}
),
blueprint AS (
  SELECT seb.id FROM wix_site_experience_blueprints seb
  JOIN project p ON p.id = seb.launch_project_id
  WHERE seb.blueprint_key = {sql_literal(BLUEPRINT_KEY)}
  ORDER BY seb.created_at LIMIT 1
),
pkg AS (
  INSERT INTO fable_uiux_handoff_packages
    (launch_project_id, site_experience_blueprint_id, package_key, package_status,
     concise_prompt_artifact_path, detailed_brief_artifact_path,
     contains_private_contact_data, contains_secrets, contains_unverified_claims,
     fable_call_made, external_call_made, human_review_required, raw_context)
  SELECT p.id, b.id, {sql_literal(PACKAGE_KEY)}, 'generated',
     {sql_literal(rel(concise_path))}, {sql_literal(rel(detailed_path))},
     false, false, true, false, false, true,
     jsonb_build_object('phase','{PHASE}','source','{SOURCE}','artifact_sha256',{sql_literal(digest)})
  FROM project p JOIN blueprint b ON true
  RETURNING id, launch_project_id
),
sections AS (
  INSERT INTO fable_uiux_handoff_sections
    (handoff_package_id, section_key, section_type, section_status, included_in_concise_prompt,
     included_in_detailed_brief, safe_summary, raw_context)
  SELECT pkg.id, s.section_key, s.section_type, 'draft', s.in_concise, true, s.safe_summary,
    jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
  FROM pkg
  JOIN (VALUES {section_rows}) AS s(section_key, section_type, in_concise, safe_summary) ON true
  RETURNING id
),
validations AS (
  INSERT INTO fable_uiux_handoff_validation_results
    (handoff_package_id, validation_type, validation_status, safe_summary, raw_context)
  SELECT pkg.id, v.validation_type, v.validation_status, v.safe_summary,
    jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
  FROM pkg
  JOIN (VALUES {validation_rows}) AS v(validation_type, validation_status, safe_summary) ON true
  RETURNING id
)
INSERT INTO fable_uiux_handoff_review_items
  (launch_project_id, handoff_package_id, review_type, status, priority, raw_context)
SELECT pkg.launch_project_id, pkg.id, r.review_type, 'pending', r.priority,
  jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
FROM pkg
JOIN (VALUES {review_rows}) AS r(review_type, priority) ON true;

DO $LIVE_GUARD$
DECLARE called int; ext int; inbound int; contacts_count int; send_count int; publish_count int;
BEGIN
  SELECT count(*) INTO called FROM fable_uiux_handoff_packages hp JOIN launch_projects p ON p.id = hp.launch_project_id
    WHERE p.launch_key = {lk} AND hp.fable_call_made;
  SELECT count(*) INTO ext FROM fable_uiux_handoff_packages hp JOIN launch_projects p ON p.id = hp.launch_project_id
    WHERE p.launch_key = {lk} AND hp.external_call_made;
  SELECT count(*) INTO inbound FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  SELECT send_enabled_count INTO send_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT publish_enabled_count INTO publish_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  IF called > 0 OR ext > 0 THEN RAISE EXCEPTION 'Refusing: package flags indicate Fable/external call.'; END IF;
  IF inbound <> 0 THEN RAISE EXCEPTION 'Refusing: inbound lead count changed to %.', inbound; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 THEN RAISE EXCEPTION 'Refusing: send/publish enabled.'; END IF;
END $LIVE_GUARD$;

COMMIT;

SELECT 'handoff_packages', count(*)::text FROM fable_uiux_handoff_packages hp JOIN launch_projects p ON p.id = hp.launch_project_id WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'sections', count(*)::text FROM fable_uiux_handoff_sections s JOIN fable_uiux_handoff_packages hp ON hp.id = s.handoff_package_id JOIN launch_projects p ON p.id = hp.launch_project_id WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'validation_results', count(*)::text FROM fable_uiux_handoff_validation_results vr JOIN fable_uiux_handoff_packages hp ON hp.id = vr.handoff_package_id JOIN launch_projects p ON p.id = hp.launch_project_id WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'review_items', count(*)::text FROM fable_uiux_handoff_review_items ri JOIN fable_uiux_handoff_packages hp ON hp.id = ri.handoff_package_id JOIN launch_projects p ON p.id = hp.launch_project_id WHERE p.launch_key = {lk} AND hp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'fable_call_made_count', fable_call_made_count::text FROM vw_dlf_fable_handoff_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'external_call_made_count', external_call_made_count::text FROM vw_dlf_fable_handoff_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_fable_use', ready_for_fable_use::text FROM vw_dlf_fable_handoff_readiness WHERE launch_key = {lk}
ORDER BY 1;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Create DLF Westpark Fable UI/UX handoff package. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR.relative_to(PROJECT_ROOT)))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    concise_path, detailed_path = artifact_paths(args.output_dir)
    print(f"DLF Westpark Fable UI/UX handoff package. launch_key={args.launch_key}. Counts only.")
    print(f"concise_prompt_artifact_path={concise_path}")
    print(f"detailed_brief_artifact_path={detailed_path}")

    strategy = fetch_strategy(args.launch_key)
    if not strategy:
        print("Refusing: could not load the approved Phase 7.15 design strategy for this launch key.")
        return 1

    concise = build_concise_prompt(strategy)
    detailed = build_detailed_brief(strategy)
    checks = validate_artifacts(concise, detailed)
    digest = hashlib.sha256((concise + detailed).encode("utf-8")).hexdigest()
    failures = sum(1 for s in checks.values() if s != "passed")

    print("projected:")
    print("  handoff packages: 1")
    print(f"  sections: {len(SECTIONS)}")
    print(f"  validation results: {len(VALIDATIONS)}  (failures: {failures})")
    print(f"  review items: {len(REVIEWS)}")
    print(f"  concise prompt chars: {len(concise)} (budget {CONCISE_CHAR_BUDGET})")
    print("  fable_call_made: 0   external_call_made: 0   wix/meta/whatsapp/email/n8n calls: 0")
    print("  publishing: 0   live_forms: 0   live_webhooks: 0")
    print("  inbound_leads_created: 0   contacts_created_or_merged: 0   messages_sent: 0")
    print("  validations:")
    for v in VALIDATIONS:
        print(f"    {v}: {checks[v]}")

    if failures:
        print("Refusing: artifact validation failed before writing.")
        return 1

    if not (args.apply and args.real_ok):
        print("Dry run only. No artifact or database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    concise_path.parent.mkdir(parents=True, exist_ok=True)
    concise_path.write_text(concise, encoding="utf-8")
    detailed_path.write_text(detailed, encoding="utf-8")

    code, output = run_psql(apply_sql(args.launch_key, concise_path, detailed_path, digest, checks))
    print("Apply result:" if code == 0 else "Apply FAILED:")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
