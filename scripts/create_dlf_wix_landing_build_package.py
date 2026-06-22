#!/usr/bin/env python3
"""Phase 7.14 — create a DLF Wix landing page + lead form build package.

The package is a local Markdown artifact plus tracking/validation/review DB rows
for a HUMAN to build the page manually in Wix. It performs NO Wix API calls, NO
page creation, NO publishing, NO live form/webhook creation, NO sends, and NO
inbound-lead/contact writes. Unverified facts stay as placeholders.

Dry-run by default. Writing the artifact and DB rows requires BOTH --real-ok and
--apply. The artifact is written under the git-ignored exports/wix_build_packages/
directory only. Counts only, plus artifact path.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.14"
SOURCE = "dlf_wix_landing_build_package"
PACKAGE_KEY = "dlf-westpark-wix-landing-build"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "exports" / "wix_build_packages"

# Factual placeholders that must remain unresolved in any generated artifact.
FACTUAL_PLACEHOLDERS = (
    "RERA_VERIFY",
    "PRICE_VERIFY",
    "BROCHURE_LINK_PENDING",
    "WIX_PAGE_PENDING",
    "VERIFY",
    "VISUAL_DIRECTION_PENDING",
)

# Phrases that must never appear in a compliant artifact.
FORBIDDEN_PHRASES = (
    "guaranteed return",
    "guaranteed returns",
    "assured return",
    "limited time only",
    "hurry",
    "last few units",
    "only a few left",
    "selling fast",
    "book before price rises",
)

VALIDATIONS = (
    "no_secrets",
    "no_contact_data",
    "factual_placeholders_preserved",
    "consent_fields_present",
    "utm_fields_present",
    "no_publish_enabled",
    "no_live_webhook",
    "seo_sections_present",
)

REVIEWS = (
    ("landing_page_build_review", "high"),
    ("lead_form_build_review", "high"),
    ("seo_review", "normal"),
    ("consent_review", "blocker"),
    ("factual_claim_review", "blocker"),
    ("publish_blocker_review", "blocker"),
)
def fetch_spec(launch_key: str) -> dict | None:
    """Pull the landing page spec, lead form, field mappings, and pillars.

    Returns structural/marketing fields only. No contact rows are read; field
    mappings expose mapping metadata (labels/types/pii_type), never lead values.
    """
    lk = sql_literal(launch_key)
    sql = f"""
SELECT json_build_object(
  'project_id', p.id,
  'display_name', COALESCE(p.project_display_name, 'DLF Westpark'),
  'landing', (
    SELECT to_json(s) FROM (
      SELECT id, page_key, page_title, page_slug, page_status,
             hero_headline, hero_subheadline, primary_cta, secondary_cta,
             form_goal, required_sections, trust_disclaimers,
             rera_disclaimer_required, publish_enabled
      FROM launch_landing_page_specs
      WHERE launch_project_id = p.id
      ORDER BY created_at LIMIT 1
    ) s
  ),
  'form', (
    SELECT to_json(f) FROM (
      SELECT id, form_key, form_status, form_goal, required_fields,
             qualification_questions, consent_fields, utm_capture_required,
             whatsapp_optin_required, email_optin_required, publish_enabled
      FROM launch_lead_capture_forms
      WHERE launch_project_id = p.id
      ORDER BY created_at LIMIT 1
    ) f
  ),
  'field_mappings', (
    SELECT COALESCE(json_agg(m ORDER BY m.field_key), '[]'::json) FROM (
      SELECT field_key, field_label, field_type, required, pii_type, mapping_status
      FROM launch_lead_field_mappings
      WHERE launch_project_id = p.id
    ) m
  ),
  'pillars', (
    SELECT COALESCE(json_agg(c ORDER BY c.pillar_key), '[]'::json) FROM (
      SELECT pillar_key, pillar_name, audience_segment, funnel_stage, core_message
      FROM launch_content_pillars
      WHERE launch_project_id = p.id
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
        return json.loads(output)
    except json.JSONDecodeError:
        return None

def build_markdown(launch_key: str, spec: dict) -> str:
    """Render a human-buildable Wix build package as Markdown.

    Marketing copy and structure only. Factual claims (RERA, price, area,
    brochure, visuals) stay as placeholders. No secrets, no contact data, no
    live URLs, no scarcity/guarantee claims.
    """
    display_name = spec.get("display_name") or "DLF Westpark"
    landing = spec.get("landing") or {}
    form = spec.get("form") or {}
    mappings = spec.get("field_mappings") or []
    pillars = spec.get("pillars") or []

    slug = landing.get("page_slug") or "dlf-westpark-andheri-west"
    page_title = landing.get("page_title") or f"{display_name} — Andheri West"

    lines: list[str] = []
    lines.append(f"# Wix Build Package — {display_name}")
    lines.append("")
    lines.append("> HUMAN-BUILD ONLY. This document is an operator checklist for building the")
    lines.append("> page manually in Wix. It is NOT published, NOT connected to Wix APIs, and")
    lines.append("> contains NO live form/webhook. Factual placeholders below MUST be resolved")
    lines.append("> by a human with verified sources before any publish review.")
    lines.append("")
    lines.append(f"- launch_key: `{launch_key}`")
    lines.append(f"- confirmed_project_name: `{display_name}`")
    lines.append(f"- page_status: `{landing.get('page_status', 'draft')}` (publish_enabled stays false)")
    lines.append(f"- page artifact placeholder: `WIX_PAGE_PENDING`")
    lines.append("")

    lines.append("## 1. Page identity")
    lines.append(f"- Page title: {page_title}")
    lines.append(f"- Slug suggestion: `/{slug}`")
    lines.append("")

    lines.append("## 2. Hero section")
    lines.append(f"- Headline: {landing.get('hero_headline') or '[VERIFY]'}")
    lines.append(f"- Subheadline: {landing.get('hero_subheadline') or '[VERIFY]'}")
    lines.append("- Hero visual direction: VISUAL_DIRECTION_PENDING")
    lines.append("- RERA registration line: RERA_VERIFY (display only after human verification)")
    lines.append("")

    lines.append("## 3. CTA sections")
    lines.append(f"- Primary CTA: {landing.get('primary_cta') or 'Request details'}")
    lines.append(f"- Secondary CTA: {landing.get('secondary_cta') or 'Download brochure'} (brochure: BROCHURE_LINK_PENDING)")
    lines.append("- CTA target: in-page lead form (no external/live webhook; manual review queue only)")
    lines.append("")

    lines.append("## 4. Lead form field list")
    lines.append(f"- form_key: `{form.get('form_key', 'n/a')}`  form_status: `{form.get('form_status', 'draft')}`  publish_enabled: false")
    if mappings:
        lines.append("- Fields (label / type / required / pii_type / mapping_status):")
        for m in mappings:
            lines.append(
                f"  - {m.get('field_label', m.get('field_key'))} / {m.get('field_type', 'text')} / "
                f"required={str(m.get('required', False)).lower()} / pii={m.get('pii_type', 'none')} / "
                f"{m.get('mapping_status', 'draft')}"
            )
    else:
        lines.append("  - [VERIFY] no field mappings found")
    lines.append("")

    lines.append("## 5. Consent / opt-in fields (required, unchecked by default)")
    consent_fields = form.get("consent_fields")
    if isinstance(consent_fields, list) and consent_fields:
        for c in consent_fields:
            lines.append(f"- {c}")
    else:
        lines.append("- Consent to be contacted about this project (explicit opt-in checkbox)")
    lines.append(f"- WhatsApp opt-in required: {str(form.get('whatsapp_optin_required', True)).lower()} (separate, unchecked by default)")
    lines.append(f"- Email opt-in required: {str(form.get('email_optin_required', True)).lower()} (separate, unchecked by default)")
    lines.append("- Privacy policy link and opt-out notice required near submit button")
    lines.append("")

    lines.append("## 6. UTM hidden fields (capture only; not displayed)")
    lines.append(f"- utm_capture_required: {str(form.get('utm_capture_required', True)).lower()}")
    for utm in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"):
        lines.append(f"- {utm} (hidden input)")
    lines.append("")

    lines.append("## 7. SEO title / meta placeholders")
    lines.append(f"- SEO title: {page_title} | [VERIFY]")
    lines.append("- Meta description: [VERIFY] — keep factual; no price/RERA claims until verified")
    lines.append(f"- Canonical slug: `/{slug}`")
    lines.append("- Open Graph image: VISUAL_DIRECTION_PENDING")
    lines.append("")

    lines.append("## 8. Content sections (from launch content pillars)")
    if pillars:
        for pil in pillars:
            lines.append(
                f"- {pil.get('pillar_name', pil.get('pillar_key'))} "
                f"[{pil.get('funnel_stage', 'n/a')} / {pil.get('audience_segment', 'n/a')}]: "
                f"{pil.get('core_message', '[VERIFY]')}"
            )
    else:
        lines.append("- [VERIFY] no content pillars found")
    lines.append("")

    lines.append("## 9. Unresolved factual placeholders (must be human-verified)")
    for ph in FACTUAL_PLACEHOLDERS:
        lines.append(f"- {ph}")
    lines.append("")

    lines.append("## 10. Publish blockers (all must clear via human review first)")
    lines.append("- publish_enabled = false (do not enable in this phase)")
    lines.append("- ready_for_live_lead_capture = false")
    lines.append("- ready_for_launch_push = false")
    lines.append("- RERA number not verified (RERA_VERIFY)")
    lines.append("- Price/area not verified (PRICE_VERIFY)")
    lines.append("- Brochure asset not finalized (BROCHURE_LINK_PENDING)")
    lines.append("- Consent/opt-in copy pending compliance sign-off")
    lines.append("- No live form/webhook wired (manual review queue only)")
    lines.append("")

    lines.append("## 11. Operator checklist (manual Wix build)")
    lines.append("- [ ] Create draft page in Wix (do NOT publish)")
    lines.append("- [ ] Add hero, CTA, content sections per above")
    lines.append("- [ ] Build lead form with fields + consent/opt-in checkboxes (unchecked)")
    lines.append("- [ ] Add UTM hidden inputs")
    lines.append("- [ ] Resolve every factual placeholder with a verified source")
    lines.append("- [ ] Leave form submission routed to manual review (no live webhook)")
    lines.append("- [ ] Submit page + form for human consent/factual/publish review")
    lines.append("- [ ] Keep publish disabled until launch readiness checks pass")
    lines.append("")

    return "\n".join(lines) + "\n"

NEGATIONS = ("no", "not", "without", "never", "zero")

def _forbidden_affirmative_present(lower: str) -> bool:
    """True if any forbidden phrase appears as an affirmative claim.

    A negated disclaimer (e.g. "no guaranteed returns") is compliant and ignored;
    only un-negated occurrences are treated as false scarcity/guarantee claims.
    """
    import re
    for phrase in FORBIDDEN_PHRASES:
        for match in re.finditer(re.escape(phrase), lower):
            prefix = lower[max(0, match.start() - 24):match.start()]
            preceding = re.findall(r"[a-z]+", prefix)
            if preceding and preceding[-1] in NEGATIONS:
                continue
            return True
    return False

def validate_markdown(markdown: str) -> dict[str, str]:
    lower = markdown.lower()
    placeholders_present = all(ph in markdown for ph in FACTUAL_PLACEHOLDERS)
    forbidden_present = _forbidden_affirmative_present(lower)
    has_consent = "consent" in lower and "opt-in" in lower
    has_utm = "utm_source" in lower and "hidden" in lower
    has_seo = "seo title" in lower and "meta description" in lower
    no_live_url = "http://" not in lower and "https://" not in lower
    no_publish = "publish_enabled = false" in lower
    # Contact-data heuristic: no raw email addresses or long digit runs.
    import re
    has_email = bool(re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", lower))
    has_phone = bool(re.search(r"\d{7,}", markdown))
    # secrets heuristic
    has_secret = any(tok in lower for tok in ("password", "api_key", "apikey", "secret", "access_token", "bearer "))
    return {
        "no_secrets": "passed" if not has_secret else "failed",
        "no_contact_data": "passed" if not (has_email or has_phone) else "failed",
        "factual_placeholders_preserved": "passed" if placeholders_present and not forbidden_present else "failed",
        "consent_fields_present": "passed" if has_consent else "failed",
        "utm_fields_present": "passed" if has_utm else "failed",
        "no_publish_enabled": "passed" if no_publish else "failed",
        "no_live_webhook": "passed" if no_live_url else "failed",
        "seo_sections_present": "passed" if has_seo else "failed",
    }

def artifact_path_for(output_dir: str) -> Path:
    out = Path(output_dir)
    if not out.is_absolute():
        out = PROJECT_ROOT / out
    return out / f"{PACKAGE_KEY}.md"

def apply_sql(launch_key: str, artifact_path: Path, digest: str, checks: dict[str, str]) -> str:
    lk = sql_literal(launch_key)
    rel_artifact = artifact_path.relative_to(PROJECT_ROOT) if artifact_path.is_relative_to(PROJECT_ROOT) else artifact_path
    validation_rows = []
    for vtype in VALIDATIONS:
        status = checks[vtype]
        validation_rows.append(
            f"({sql_literal(vtype)}, {sql_literal(status)}, {sql_literal(vtype + ' -> ' + status)})"
        )
    review_rows = ", ".join(f"({sql_literal(rtype)}, {sql_literal(priority)})" for rtype, priority in REVIEWS)
    return f"""
BEGIN;

DO $GUARD$
DECLARE unsafe int; approved int;
BEGIN
  SELECT count(*) INTO unsafe
  FROM launch_wix_build_packages bp
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk}
    AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}'
    AND (bp.wix_page_created OR bp.wix_page_published OR bp.live_form_created OR bp.external_call_made);
  SELECT count(*) INTO approved
  FROM launch_wix_build_packages bp
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk}
    AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}'
    AND bp.package_status IN ('built_in_wix', 'published', 'approved_for_manual_build');
  IF unsafe > 0 THEN RAISE EXCEPTION 'Refusing: existing Phase 7.14 Wix package is marked created/published/live/external.'; END IF;
  IF approved > 0 THEN RAISE EXCEPTION 'Refusing: existing Phase 7.14 Wix package already approved/built/published.'; END IF;
END $GUARD$;

DELETE FROM launch_wix_build_review_items ri
USING launch_wix_build_packages bp, launch_projects p
WHERE ri.build_package_id = bp.id
  AND bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';

DELETE FROM launch_wix_build_validation_results vr
USING launch_wix_build_packages bp, launch_projects p
WHERE vr.build_package_id = bp.id
  AND bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';

DELETE FROM launch_wix_build_packages bp
USING launch_projects p
WHERE bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';

WITH project AS (
  SELECT id FROM launch_projects WHERE launch_key = {lk}
),
landing AS (
  SELECT s.id FROM launch_landing_page_specs s
  JOIN project p ON p.id = s.launch_project_id
  ORDER BY s.created_at LIMIT 1
),
form AS (
  SELECT f.id FROM launch_lead_capture_forms f
  JOIN project p ON p.id = f.launch_project_id
  ORDER BY f.created_at LIMIT 1
),
pkg AS (
  INSERT INTO launch_wix_build_packages
    (launch_project_id, landing_page_spec_id, lead_capture_form_id, package_key, package_status,
     artifact_path, artifact_type, contains_secrets, contains_contact_data, contains_unverified_claims,
     external_call_made, wix_page_created, wix_page_published, live_form_created, human_review_required,
     raw_context)
  SELECT p.id, l.id, f.id, {sql_literal(PACKAGE_KEY)}, 'validated', {sql_literal(str(rel_artifact))},
     'wix_landing_page_build_markdown', false, false, true, false, false, false, false, true,
     jsonb_build_object('phase','{PHASE}','source','{SOURCE}','artifact_sha256',{sql_literal(digest)})
  FROM project p
  JOIN landing l ON true
  JOIN form f ON true
  RETURNING id, launch_project_id
),
validations AS (
  INSERT INTO launch_wix_build_validation_results
    (build_package_id, validation_type, validation_status, safe_summary, raw_context)
  SELECT pkg.id, v.validation_type, v.validation_status, v.safe_summary,
    jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
  FROM pkg
  JOIN (VALUES {", ".join(validation_rows)}) AS v(validation_type, validation_status, safe_summary) ON true
  RETURNING id, build_package_id
)
INSERT INTO launch_wix_build_review_items
  (launch_project_id, build_package_id, review_type, status, priority, raw_context)
SELECT pkg.launch_project_id, pkg.id, r.review_type, 'pending', r.priority,
  jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
FROM pkg
JOIN (VALUES {review_rows}) AS r(review_type, priority) ON true;

DO $LIVE_GUARD$
DECLARE created int; published int; liveform int; inbound int; contacts_count int; send_count int; publish_count int;
BEGIN
  SELECT count(*) INTO created FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
    WHERE p.launch_key = {lk} AND bp.wix_page_created;
  SELECT count(*) INTO published FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
    WHERE p.launch_key = {lk} AND bp.wix_page_published;
  SELECT count(*) INTO liveform FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
    WHERE p.launch_key = {lk} AND bp.live_form_created;
  SELECT count(*) INTO inbound FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  SELECT send_enabled_count INTO send_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT publish_enabled_count INTO publish_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  IF created > 0 OR published > 0 OR liveform > 0 THEN RAISE EXCEPTION 'Refusing: package flags indicate Wix page/publish/live form.'; END IF;
  IF inbound <> 0 THEN RAISE EXCEPTION 'Refusing: inbound lead count changed to %.', inbound; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 THEN RAISE EXCEPTION 'Refusing: send/publish enabled.'; END IF;
END $LIVE_GUARD$;

COMMIT;

SELECT 'build_packages', count(*)::text FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'validation_results', count(*)::text FROM launch_wix_build_validation_results vr JOIN launch_wix_build_packages bp ON bp.id = vr.build_package_id JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'review_items', count(*)::text FROM launch_wix_build_review_items ri JOIN launch_wix_build_packages bp ON bp.id = ri.build_package_id JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'wix_page_created', count(*)::text FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.wix_page_created
UNION ALL SELECT 'wix_page_published', count(*)::text FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.wix_page_published
UNION ALL SELECT 'live_form_created', count(*)::text FROM launch_wix_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.live_form_created
UNION ALL SELECT 'ready_to_publish', ready_to_publish::text FROM vw_dlf_wix_build_readiness WHERE launch_key = {lk}
ORDER BY 1;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Create DLF Wix landing/form build package. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR.relative_to(PROJECT_ROOT)))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    artifact_path = artifact_path_for(args.output_dir)
    print(f"DLF Wix landing build package. launch_key={args.launch_key}. Counts only.")
    print(f"artifact_path={artifact_path}")

    spec = fetch_spec(args.launch_key)
    if not spec:
        print("Refusing: could not load landing/form/pillar spec for launch key.")
        return 1

    markdown = build_markdown(args.launch_key, spec)
    checks = validate_markdown(markdown)
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    failures = sum(1 for status in checks.values() if status != "passed")

    print("projected:")
    print("  build packages: 1")
    print(f"  validation results: {len(VALIDATIONS)}  (failures: {failures})")
    print(f"  review items: {len(REVIEWS)}")
    print(f"  field mappings rendered: {len(spec.get('field_mappings') or [])}")
    print(f"  content pillars rendered: {len(spec.get('pillars') or [])}")
    print("  wix_api_calls: 0   wix_page_created: 0   wix_page_published: 0   live_form_created: 0")
    print("  inbound_leads_created: 0   contacts_created_or_merged: 0   sends_or_publishing: 0")
    print("  validations:")
    for vtype in VALIDATIONS:
        print(f"    {vtype}: {checks[vtype]}")

    if failures:
        print("Refusing: local artifact validation failed before writing.")
        return 1

    if not (args.apply and args.real_ok):
        print("Dry run only. No artifact or database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(markdown, encoding="utf-8")

    code, output = run_psql(apply_sql(args.launch_key, artifact_path, digest, checks))
    print("Apply result:" if code == 0 else "Apply FAILED:")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
