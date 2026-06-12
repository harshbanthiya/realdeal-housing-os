#!/usr/bin/env python3
"""Phase 7.17 — capture the manually-generated Fable "Gallery White" design output and
the Gemini second-opinion critique for DLF Westpark into review-gated DB rows.

The raw Fable/Gemini artifacts live ONLY on disk under the git-ignored exports/ tree.
This script stores nothing but filesystem paths plus curated, business-safe summaries
and the concrete design refinement actions extracted from the critique. It performs NO
Fable call, NO Gemini call, NO Wix API call, NO external API call, NO publishing, NO
live form/webhook, NO sends, and NO inbound-lead/contact writes.

Before writing, every text artifact is scanned and the run is REFUSED if it contains an
obvious email, a long phone-like string, a leaked DB UUID, or a secret/API-key pattern.
Dry-run by default; writing requires BOTH --real-ok and --apply. Counts only — full
artifact contents are never printed or stored.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
EXPORTS_ROOT = PROJECT_ROOT / "exports"
PHASE = "7.17"
SOURCE = "fable_gemini_design_output_capture"
OUTPUT_KEY = "dlf-westpark-gallery-white-v1"
DESIGN_DIRECTION_NAME = "DLF Westpark — Gallery White"
GEMINI_REVIEW_KEY = "dlf-westpark-gallery-white-v1-gemini"

DEFAULT_FABLE_OUTPUT = "exports/fable_outputs/dlf-westpark-gallery-white-v1/fable-output-full.md"
DEFAULT_FABLE_PREVIEW = "exports/fable_outputs/dlf-westpark-gallery-white-v1/preview.png"
DEFAULT_GEMINI_REVIEW = "exports/design_reviews/dlf-westpark-gallery-white-v1/gemini-review.md"

OUTPUT_SAFE_SUMMARY = (
    "Fable 'Gallery White' design direction for the DLF Westpark website: editorial, "
    "white-dominant luxury system with deep-teal anchors, Manrope type, monospace "
    "placeholder tokens for unverified facts, type-first hero, seven-section landing "
    "narrative, manual-review lead form (no live webhook), and a Wix build map. "
    "Design-only deliverable; nothing was published or wired."
)

GEMINI_SAFE_SUMMARY = (
    "Gemini second-opinion critique of 'Gallery White': praises the disciplined, "
    "premium editorial system but flags branding disconnect (warm faceted logo vs cold "
    "minimal UI), type-first hero hiding imagery, a section-05 typography wall, dropped "
    "mobile navigation, placeholder fatigue, SEO heading semantics, form tap-target "
    "clarity, image CLS risk, and sticky-CTA/footer overlap. Ten actionable improvements "
    "for the Wix build."
)

# (action_key, action_category, priority, safe_summary, wix_implementation_note, fable_followup_note)
REFINEMENT_ACTIONS = [
    (
        "hero_visual_context", "hero", "high",
        "Type-first hero pushes all imagery below the fold; reveal a slice of the 16:7 "
        "hero image (or a split layout) above the fold to anchor the eye downward.",
        "Compress hero vertical padding or use a split container so the top of the hero "
        "image peeks above the fold while keeping the type-first hierarchy.",
        "Adjust the hero spec to surface a portion of the hero image above the fold "
        "without abandoning the type-first headline order.",
    ),
    (
        "perspective_asym_layout", "brand", "normal",
        "Section 05 (Perspective) is centered prose only and risks a 'wall of text' "
        "drop-off; an asymmetric editorial layout keeps the artistic tone.",
        "Two-column asymmetric strip: large muted '05' numeral or architectural detail "
        "left, the editorial statement pushed right.",
        "Reformat section 05 from centered prose into an asymmetric numeral-plus-statement "
        "composition.",
    ),
    (
        "mini_map_toggle", "imagery", "normal",
        "The fully static location-map card can read as low-effort; a pseudo-interactive "
        "toggle adds premium utility while staying fast and compliant (no live embed).",
        "Use a Wix multi-state box: ledger tabs (Transit / Schools / Retail) swap the "
        "static map image; no live map embed until tracking review passes.",
        "Note an optional multi-state static-map interaction for section 02 in any "
        "follow-up spec; live embeds stay deferred.",
    ),
    (
        "intent_auto_select", "form_ux", "high",
        "Clicking 'Request details' on a Residences row should auto-select the matching "
        "intent pill in the form instead of forcing a second manual selection.",
        "Use a Wix Velo handler or URL parameter to scroll to the form and pre-select the "
        "corresponding intent pill on configuration-row clicks.",
        "Extend the form intent pre-fill spec to auto-scroll and auto-select the intent "
        "pill from Residences-row clicks.",
    ),
    (
        "branded_placeholder_status", "compliance", "high",
        "If every unverified value shows a robotic VERIFY token at launch, the page can "
        "look unfinished; a branded micro-copy status reads as intentional. It must remain "
        "an honest 'pending' wrapper and never imply a fabricated value.",
        "Replace bare VERIFY/PRICE_VERIFY/RERA_VERIFY display strings with a branded "
        "monospace status such as '[Pricing under internal review]'; keep the mono "
        "aesthetic and never substitute a fake number.",
        "Offer an optional branded placeholder-status style for pending facts while "
        "preserving the literal placeholder semantics (no invented values).",
    ),
    (
        "mobile_nav_scroll_reveal", "navigation", "high",
        "Dropping mobile navigation entirely (mark + Enquire pill, footer-only nav) forces "
        "long thumb-scrolling to reach sections like floor plans.",
        "Keep a sticky top nav on mobile, or add a scroll-up-reveal anchor/hamburger that "
        "appears only on upward scroll.",
        "Revisit the mobile nav spec to add a lightweight scroll-up-reveal section nav "
        "rather than removing navigation outright.",
    ),
    (
        "semantic_seo_heading_strategy", "seo", "high",
        "The 'max two type sizes per section' rule limits nested H3/H4 structure that "
        "search engines use to understand long-form real-estate pages.",
        "On long-form area/building SEO pages, style the 13px mono token as real H3/H4 "
        "HTML headings so crawlers see nested structure without visual clutter; keep one "
        "H1 per page.",
        "Add a semantic-heading note: visually-quiet text may still map to H3/H4 tags on "
        "SEO pages while respecting one-H1-per-page.",
    ),
    (
        "input_target_fill", "form_ux", "normal",
        "Underline-only fields can be hard for older or vision-impaired users to locate, "
        "lowering form completion.",
        "Give inputs a subtle mist (#F4F7F8) fill that transitions to white on focus to "
        "define the tap/click target while keeping the minimal look.",
        "Refine the form-field spec so inputs carry a soft fill defining the target area "
        "instead of a bare bottom border.",
    ),
    (
        "fixed_image_aspect_ratios", "performance", "high",
        "The real performance risk under the LCP/CLS budget is layout shift during image "
        "load, not file size (Wix auto-compresses).",
        "Set explicit aspect-ratio dimensions on every Wix image container so layout stays "
        "stable while images wipe in, keeping CLS near zero.",
        "Reinforce in any follow-up that image frames must declare fixed aspect ratios to "
        "protect CLS.",
    ),
    (
        "sticky_cta_intersection_hide", "mobile", "normal",
        "The mobile sticky bar must retract cleanly so it never overlaps the form buttons "
        "or legal links near the footer.",
        "Use an intersection trigger so the mobile sticky bar fades out ~100px before the "
        "form and stays hidden through the footer.",
        "Tighten the sticky-CTA spec with an explicit intersection hide-before-form and "
        "stay-hidden-through-footer rule.",
    ),
    (
        "logo_brand_grounding", "brand", "high",
        "The warm, multi-faceted Real Deal Housing logo and the mass-market name sit in "
        "tension with the cold, boutique 'Gallery White' UI; the mark can look jarring.",
        "Ground the layout in the logo's deep-teal (#1F3D4D) and use the warm roof facets "
        "only as the specified eyebrow ticks so the mark reads as one brand.",
        "Add brand-grounding guidance so the logo's teal anchors the palette and roof "
        "facets stay confined to tick accents.",
    ),
    (
        "warmth_against_cold_minimalism", "brand", "normal",
        "Pure cold minimalism can feel clinical for a home purchase; controlled warmth "
        "builds trust without breaking the restrained aesthetic.",
        "Introduce limited warmth via facet accents and warmth-balanced imagery grading "
        "while honoring 'one warm accent per viewport'.",
        "Note a controlled-warmth direction so imagery and accents add human warmth within "
        "the existing accent budget.",
    ),
]

EMAIL_RE = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?91[\s-]?)?\d{10}(?!\w)")
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
SECRET_TOKENS = ("password", "api_key", "apikey", "access_token", "secret_key", "bearer ", "-----begin")
NEGATIONS = ("no", "not", "without", "never", "zero")


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


def resolve_under_exports(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p.resolve()


def is_under_exports(path: Path) -> bool:
    try:
        return path.is_relative_to(EXPORTS_ROOT.resolve())
    except AttributeError:  # pragma: no cover (py<3.9)
        return str(path).startswith(str(EXPORTS_ROOT.resolve()))


def _secret_present(lower: str) -> bool:
    for tok in SECRET_TOKENS:
        for match in re.finditer(re.escape(tok), lower):
            prefix = lower[max(0, match.start() - 20):match.start()]
            preceding = re.findall(r"[a-z]+", prefix)
            if preceding and preceding[-1] in NEGATIONS:
                continue
            return True
    return False


def scan_text_artifact(path: Path) -> dict:
    """Scan a text artifact for leakage. Returns counts only — never the matched text."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()
    return {
        "emails": len(EMAIL_RE.findall(lower)),
        "phones": len(PHONE_RE.findall(text)),
        "uuids": len(UUID_RE.findall(lower)),
        "secrets": 1 if _secret_present(lower) else 0,
        "bytes": len(text.encode("utf-8")),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def build_ctx(extra: dict | None = None) -> str:
    pairs = [
        "'phase'", f"'{PHASE}'",
        "'source'", f"'{SOURCE}'",
        "'external_calls_made'", "false",
        "'fable_call_made'", "false",
        "'wix_api_call_made'", "false",
        "'publish_enabled'", "false",
        "'communication_sent'", "false",
    ]
    if extra:
        for k, v in extra.items():
            pairs.append(sql_literal(k))
            pairs.append(sql_literal(v))
    return "jsonb_build_object(" + ", ".join(pairs) + ")"


def build_apply_sql(launch_key: str, fable_path: Path, preview_path: Path | None,
                    gemini_path: Path | None, fable_scan: dict) -> str:
    lk = sql_literal(launch_key)
    has_gemini = gemini_path is not None
    ctx = build_ctx()

    action_rows = ",\n      ".join(
        "(" + ", ".join([
            sql_literal(key), sql_literal(cat), sql_literal(pri),
            sql_literal(summary), sql_literal(wix_note), sql_literal(fable_note),
        ]) + ")"
        for key, cat, pri, summary, wix_note, fable_note in REFINEMENT_ACTIONS
    )

    sop_cte = ""
    sop_join = ""
    sop_ref_actions = "NULL"
    sop_ref_review = "NULL"
    gemini_review_cte = ""
    if has_gemini:
        sop_cte = f"""
sop AS (
  INSERT INTO design_second_opinion_reviews
    (launch_project_id, fable_design_output_id, review_key, review_source, review_status,
     raw_artifact_path, safe_summary, contains_private_contact_data, contains_secrets,
     external_call_made, human_review_required, raw_context)
  SELECT out.launch_project_id, out.id, {sql_literal(GEMINI_REVIEW_KEY)}, 'gemini', 'captured',
     {sql_literal(rel(gemini_path))}, {sql_literal(GEMINI_SAFE_SUMMARY)},
     false, false, false, true, {ctx}
  FROM out
  RETURNING id
),"""
        sop_join = "CROSS JOIN sop"
        sop_ref_actions = "sop.id"
        sop_ref_review = "sop.id"
        gemini_review_cte = f"""
gemini_review AS (
  INSERT INTO fable_design_review_items
    (launch_project_id, fable_design_output_id, second_opinion_review_id, review_type,
     status, priority, raw_context)
  SELECT out.launch_project_id, out.id, sop.id, 'gemini_review_review', 'pending', 'high', {ctx}
  FROM out CROSS JOIN sop
  RETURNING id
),"""

    preview_literal = sql_literal(rel(preview_path)) if preview_path is not None else "NULL"

    return f"""
BEGIN;

DO $GUARD$
DECLARE locked int;
BEGIN
  SELECT count(*) INTO locked
  FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id
  WHERE p.launch_key = {lk}
    AND o.raw_context->>'phase' = '{PHASE}' AND o.raw_context->>'source' = '{SOURCE}'
    AND (o.output_status = 'accepted_direction' OR o.external_call_made);
  IF locked > 0 THEN RAISE EXCEPTION 'Refusing: existing Phase 7.17 output is accepted/external; re-capture blocked.'; END IF;

  SELECT count(*) INTO locked
  FROM design_second_opinion_reviews r JOIN launch_projects p ON p.id = r.launch_project_id
  WHERE p.launch_key = {lk}
    AND r.raw_context->>'phase' = '{PHASE}' AND r.raw_context->>'source' = '{SOURCE}'
    AND (r.review_status IN ('accepted_guidance', 'partially_accepted') OR r.external_call_made);
  IF locked > 0 THEN RAISE EXCEPTION 'Refusing: existing Phase 7.17 second-opinion review is accepted/external.'; END IF;

  SELECT count(*) INTO locked
  FROM design_refinement_actions a JOIN launch_projects p ON p.id = a.launch_project_id
  WHERE p.launch_key = {lk}
    AND a.raw_context->>'phase' = '{PHASE}' AND a.raw_context->>'source' = '{SOURCE}'
    AND a.action_status = 'accepted';
  IF locked > 0 THEN RAISE EXCEPTION 'Refusing: existing Phase 7.17 refinement action already accepted.'; END IF;
END $GUARD$;

DELETE FROM fable_design_review_items ri
USING launch_projects p
WHERE ri.launch_project_id = p.id AND p.launch_key = {lk}
  AND ri.raw_context->>'phase' = '{PHASE}' AND ri.raw_context->>'source' = '{SOURCE}';
DELETE FROM design_refinement_actions a
USING launch_projects p
WHERE a.launch_project_id = p.id AND p.launch_key = {lk}
  AND a.raw_context->>'phase' = '{PHASE}' AND a.raw_context->>'source' = '{SOURCE}';
DELETE FROM design_second_opinion_reviews r
USING launch_projects p
WHERE r.launch_project_id = p.id AND p.launch_key = {lk}
  AND r.raw_context->>'phase' = '{PHASE}' AND r.raw_context->>'source' = '{SOURCE}';
DELETE FROM fable_design_outputs o
USING launch_projects p
WHERE o.launch_project_id = p.id AND p.launch_key = {lk}
  AND o.raw_context->>'phase' = '{PHASE}' AND o.raw_context->>'source' = '{SOURCE}';

WITH project AS (
  SELECT id FROM launch_projects WHERE launch_key = {lk}
),
pkg AS (
  SELECT hp.id FROM fable_uiux_handoff_packages hp
  JOIN project p ON p.id = hp.launch_project_id
  ORDER BY hp.created_at LIMIT 1
),
out AS (
  INSERT INTO fable_design_outputs
    (launch_project_id, handoff_package_id, output_key, output_status, design_direction_name,
     source_tool, raw_artifact_path, preview_artifact_path, safe_summary,
     contains_private_contact_data, contains_secrets, contains_unverified_claims,
     external_call_made, human_review_required, raw_context)
  SELECT p.id, (SELECT id FROM pkg), {sql_literal(OUTPUT_KEY)}, 'captured',
     {sql_literal(DESIGN_DIRECTION_NAME)}, 'fable',
     {sql_literal(rel(fable_path))}, {preview_literal}, {sql_literal(OUTPUT_SAFE_SUMMARY)},
     false, false, true, false, true,
     {build_ctx({'artifact_sha256': fable_scan['sha256'], 'artifact_bytes': str(fable_scan['bytes'])})}
  FROM project p
  RETURNING id, launch_project_id
),{sop_cte}
acts AS (
  INSERT INTO design_refinement_actions
    (launch_project_id, fable_design_output_id, second_opinion_review_id, action_key,
     action_category, action_status, priority, safe_summary, wix_implementation_note,
     fable_followup_note, raw_context)
  SELECT out.launch_project_id, out.id, {sop_ref_actions}, a.action_key, a.action_category,
     'proposed', a.priority, a.safe_summary, a.wix_note, a.fable_note,
     {build_ctx()} || jsonb_build_object('action_category', a.action_category)
  FROM out {sop_join}
  JOIN (VALUES
      {action_rows}
  ) AS a(action_key, action_category, priority, safe_summary, wix_note, fable_note) ON true
  RETURNING id, action_key, priority
),
output_review AS (
  INSERT INTO fable_design_review_items
    (launch_project_id, fable_design_output_id, review_type, status, priority, raw_context)
  SELECT out.launch_project_id, out.id, 'fable_output_review', 'pending', 'blocker', {ctx}
  FROM out
  RETURNING id
),{gemini_review_cte}
final_reviews AS (
  INSERT INTO fable_design_review_items
    (launch_project_id, fable_design_output_id, second_opinion_review_id, refinement_action_id,
     review_type, status, priority, raw_context)
  SELECT out.launch_project_id, out.id, {sop_ref_review}, acts.id,
     'refinement_action_review', 'pending', acts.priority, {ctx}
  FROM out {sop_join}
  JOIN acts ON true
  RETURNING id
)
SELECT count(*) FROM final_reviews;

DO $LIVE_GUARD$
DECLARE ext int; inbound int; contacts_count int; send_count int; publish_count int;
BEGIN
  SELECT external_call_made_count INTO ext FROM vw_dlf_design_output_readiness WHERE launch_key = {lk};
  SELECT count(*) INTO inbound FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  SELECT send_enabled_count INTO send_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT publish_enabled_count INTO publish_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  IF ext > 0 THEN RAISE EXCEPTION 'Refusing: design rows marked external_call_made.'; END IF;
  IF inbound <> 0 THEN RAISE EXCEPTION 'Refusing: inbound lead count changed to %.', inbound; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 THEN RAISE EXCEPTION 'Refusing: send/publish enabled.'; END IF;
END $LIVE_GUARD$;

COMMIT;

SELECT 'fable_design_outputs', count(*)::text FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id WHERE p.launch_key = {lk} AND o.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'second_opinion_reviews', count(*)::text FROM design_second_opinion_reviews r JOIN launch_projects p ON p.id = r.launch_project_id WHERE p.launch_key = {lk} AND r.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'refinement_actions', count(*)::text FROM design_refinement_actions a JOIN launch_projects p ON p.id = a.launch_project_id WHERE p.launch_key = {lk} AND a.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'review_items', count(*)::text FROM fable_design_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'external_call_made_count', external_call_made_count::text FROM vw_dlf_design_output_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'output_accepted_count', output_accepted_count::text FROM vw_dlf_design_output_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_fable_followup', ready_for_fable_followup::text FROM vw_dlf_design_output_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_wix_design_build', ready_for_wix_design_build::text FROM vw_dlf_design_output_readiness WHERE launch_key = {lk}
ORDER BY 1;
"""


def project_exists(launch_key: str) -> bool:
    code, output = run_psql(
        f"SELECT count(*) FROM launch_projects WHERE launch_key = {sql_literal(launch_key)};"
    )
    return code == 0 and output.strip() == "1"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture DLF Westpark Fable 'Gallery White' output + Gemini review. Dry-run by default."
    )
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--fable-output-path", default=DEFAULT_FABLE_OUTPUT)
    parser.add_argument("--fable-preview-path", default=DEFAULT_FABLE_PREVIEW)
    parser.add_argument("--gemini-review-path", default=DEFAULT_GEMINI_REVIEW)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"Phase 7.17 Fable/Gemini design output capture. launch_key={args.launch_key}. Counts only.")

    if not project_exists(args.launch_key):
        print(f"Refusing: launch project '{args.launch_key}' not found.")
        return 1

    fable_path = resolve_under_exports(args.fable_output_path)
    preview_path = resolve_under_exports(args.fable_preview_path)
    gemini_path = resolve_under_exports(args.gemini_review_path)

    for label, p in (("fable-output", fable_path), ("fable-preview", preview_path), ("gemini-review", gemini_path)):
        if not is_under_exports(p):
            print(f"Refusing: {label} path is not under exports/: {p}")
            return 1

    if not fable_path.exists():
        print(f"Refusing: required Fable output artifact missing: {rel(fable_path)}")
        return 1

    fable_scan = scan_text_artifact(fable_path)
    print(f"fable_output: {rel(fable_path)}")
    print(f"  scan: emails={fable_scan['emails']} phones={fable_scan['phones']} "
          f"uuids={fable_scan['uuids']} secrets={fable_scan['secrets']} bytes={fable_scan['bytes']}")

    preview_present = preview_path.exists()
    print(f"fable_preview: {rel(preview_path)} (present={preview_present})")

    gemini_present = gemini_path.exists()
    gemini_scan = None
    if gemini_present:
        gemini_scan = scan_text_artifact(gemini_path)
        print(f"gemini_review: {rel(gemini_path)}")
        print(f"  scan: emails={gemini_scan['emails']} phones={gemini_scan['phones']} "
              f"uuids={gemini_scan['uuids']} secrets={gemini_scan['secrets']} bytes={gemini_scan['bytes']}")
    else:
        print(f"gemini_review: {rel(gemini_path)} (MISSING — second-opinion row will be skipped)")

    leakage = False
    for label, scan in (("fable", fable_scan), ("gemini", gemini_scan)):
        if scan is None:
            continue
        if scan["emails"] or scan["phones"] or scan["uuids"] or scan["secrets"]:
            print(f"Refusing: {label} artifact failed leakage scan "
                  f"(emails={scan['emails']} phones={scan['phones']} uuids={scan['uuids']} secrets={scan['secrets']}).")
            leakage = True
    if leakage:
        return 1

    n_actions = len(REFINEMENT_ACTIONS)
    n_reviews = 1 + (1 if gemini_present else 0) + n_actions
    print("projected:")
    print("  fable_design_outputs: 1")
    print(f"  second_opinion_reviews: {1 if gemini_present else 0}")
    print(f"  refinement_actions: {n_actions}")
    print(f"  review_items: {n_reviews}  (1 output + {1 if gemini_present else 0} gemini + {n_actions} action)")
    print("  external/fable/gemini/wix/meta/whatsapp/email/n8n calls: 0")
    print("  publishing: 0   live_forms: 0   live_webhooks: 0")
    print("  inbound_leads_created: 0   contacts_created_or_merged: 0   messages_sent: 0")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    sql = build_apply_sql(
        args.launch_key, fable_path,
        preview_path if preview_present else None,
        gemini_path if gemini_present else None,
        fable_scan,
    )
    code, output = run_psql(sql)
    print("Apply result:" if code == 0 else "Apply FAILED:")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
