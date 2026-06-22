#!/usr/bin/env python3
"""Phase 7.18 — approve the DLF Westpark "Gallery White" design direction. Dry-run by default.

Records human review decisions over the Phase 7.17 captured design rows ONLY:

  --accept-fable-output
      Set the Gallery White fable_design_outputs row to output_status='accepted_direction'
      and approve its fable_output_review item.
  --accept-gemini-guidance
      Set the Gemini design_second_opinion_reviews row to review_status='accepted_guidance'
      and approve its gemini_review_review item.
  --accept-core-refinements
      Set the twelve named design_refinement_actions to action_status='accepted' and approve
      their refinement_action_review items.
  --mark-build-ready-after-review  (optional, default false)
      Informational acknowledgement only: stamps the accepted output's raw_context with
      build_ready_acknowledged. The ready_for_wix_design_build signal is a COMPUTED view
      (true once the output is accepted, refinements accepted, and no design review is left
      pending) — this flag never publishes, builds, or launches anything.

It NEVER calls Fable/Gemini/Wix/Meta/WhatsApp/email/n8n, never publishes, never creates live
forms/webhooks, never touches contacts/leads/messages, never enables send/publish, and never
marks ready_for_launch_push. An in-transaction guard rolls everything back if any of those —
or any contact-data/secret/external-call flag on the reviewed rows — would be present.

Writing requires BOTH --real-ok and --apply. Counts only; never prints raw artifact contents.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.18"
CAPTURE_PHASE = "7.17"
CAPTURE_SOURCE = "fable_gemini_design_output_capture"

CORE_REFINEMENTS = (
    "hero_visual_context",
    "perspective_asym_layout",
    "mini_map_toggle",
    "intent_auto_select",
    "branded_placeholder_status",
    "mobile_nav_scroll_reveal",
    "semantic_seo_heading_strategy",
    "input_target_fill",
    "fixed_image_aspect_ratios",
    "sticky_cta_intersection_hide",
    "logo_brand_grounding",
    "warmth_against_cold_minimalism",
)
def refinements_sql() -> str:
    return ", ".join(sql_literal(k) for k in CORE_REFINEMENTS)

def capture_filter(alias: str) -> str:
    return (f"{alias}.raw_context->>'phase' = '{CAPTURE_PHASE}' "
            f"AND {alias}.raw_context->>'source' = '{CAPTURE_SOURCE}'")

def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk})
SELECT
  (SELECT count(*) FROM fable_design_outputs o WHERE o.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('o')}),
  (SELECT count(*) FROM fable_design_outputs o WHERE o.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('o')} AND o.output_status = 'accepted_direction'),
  (SELECT count(*) FROM fable_design_outputs o WHERE o.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('o')} AND (o.contains_private_contact_data OR o.contains_secrets)),
  (SELECT count(*) FROM fable_design_outputs o WHERE o.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('o')} AND o.external_call_made),
  (SELECT count(*) FROM design_second_opinion_reviews r WHERE r.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('r')}),
  (SELECT count(*) FROM design_second_opinion_reviews r WHERE r.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('r')} AND r.review_status IN ('accepted_guidance','partially_accepted')),
  (SELECT count(*) FROM design_second_opinion_reviews r WHERE r.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('r')} AND (r.contains_private_contact_data OR r.contains_secrets)),
  (SELECT count(*) FROM design_second_opinion_reviews r WHERE r.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('r')} AND r.external_call_made),
  (SELECT count(*) FROM design_refinement_actions a WHERE a.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('a')} AND a.action_key IN ({refinements_sql()})),
  (SELECT count(*) FROM design_refinement_actions a WHERE a.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('a')} AND a.action_key IN ({refinements_sql()}) AND a.action_status = 'accepted'),
  (SELECT count(*) FROM fable_design_review_items ri WHERE ri.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('ri')} AND ri.review_type = 'fable_output_review' AND ri.status = 'pending'),
  (SELECT count(*) FROM fable_design_review_items ri WHERE ri.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('ri')} AND ri.review_type = 'gemini_review_review' AND ri.status = 'pending'),
  (SELECT count(*) FROM fable_design_review_items ri WHERE ri.launch_project_id IN (SELECT id FROM proj) AND {capture_filter('ri')} AND ri.review_type = 'refinement_action_review' AND ri.status = 'pending'),
  COALESCE((SELECT ready_for_wix_design_build::text FROM vw_dlf_design_output_readiness WHERE launch_key = {lk}), 'false');
"""

def apply_sql(launch_key, reviewed_by, decision_notes, do_output, do_gemini, do_refine, build_ack):
    lk = sql_literal(launch_key)
    rb = sql_literal(reviewed_by)
    dn = sql_literal(decision_notes)
    blocks = ["BEGIN;"]

    if do_output:
        ack = ", 'build_ready_acknowledged', true" if build_ack else ""
        blocks.append(f"""
UPDATE fable_design_outputs o SET
  output_status = 'accepted_direction',
  raw_context = o.raw_context || jsonb_build_object('phase_7_18_action','output_accepted','phase_7_18_prev_output_status', o.output_status, 'phase_7_18_reviewed_by', {rb}{ack}),
  updated_at = now()
FROM launch_projects p
WHERE p.id = o.launch_project_id AND p.launch_key = {lk} AND {capture_filter('o')}
  AND o.output_status <> 'accepted_direction';

UPDATE fable_design_review_items ri SET
  status = 'approved', reviewed_by = {rb}, reviewed_at = now(), decision_notes = {dn},
  raw_context = ri.raw_context || jsonb_build_object('phase_7_18_action','item_approved','phase_7_18_prev_status', ri.status),
  updated_at = now()
FROM launch_projects p
WHERE p.id = ri.launch_project_id AND p.launch_key = {lk} AND {capture_filter('ri')}
  AND ri.review_type = 'fable_output_review' AND ri.status = 'pending';
""")

    if do_gemini:
        blocks.append(f"""
UPDATE design_second_opinion_reviews r SET
  review_status = 'accepted_guidance',
  raw_context = r.raw_context || jsonb_build_object('phase_7_18_action','gemini_accepted','phase_7_18_prev_review_status', r.review_status, 'phase_7_18_reviewed_by', {rb}),
  updated_at = now()
FROM launch_projects p
WHERE p.id = r.launch_project_id AND p.launch_key = {lk} AND {capture_filter('r')}
  AND r.review_status NOT IN ('accepted_guidance','partially_accepted');

UPDATE fable_design_review_items ri SET
  status = 'approved', reviewed_by = {rb}, reviewed_at = now(), decision_notes = {dn},
  raw_context = ri.raw_context || jsonb_build_object('phase_7_18_action','item_approved','phase_7_18_prev_status', ri.status),
  updated_at = now()
FROM launch_projects p
WHERE p.id = ri.launch_project_id AND p.launch_key = {lk} AND {capture_filter('ri')}
  AND ri.review_type = 'gemini_review_review' AND ri.status = 'pending';
""")

    if do_refine:
        blocks.append(f"""
UPDATE design_refinement_actions a SET
  action_status = 'accepted',
  raw_context = a.raw_context || jsonb_build_object('phase_7_18_action','action_accepted','phase_7_18_prev_action_status', a.action_status, 'phase_7_18_reviewed_by', {rb}),
  updated_at = now()
FROM launch_projects p
WHERE p.id = a.launch_project_id AND p.launch_key = {lk} AND {capture_filter('a')}
  AND a.action_key IN ({refinements_sql()}) AND a.action_status <> 'accepted';

UPDATE fable_design_review_items ri SET
  status = 'approved', reviewed_by = {rb}, reviewed_at = now(), decision_notes = {dn},
  raw_context = ri.raw_context || jsonb_build_object('phase_7_18_action','item_approved','phase_7_18_prev_status', ri.status),
  updated_at = now()
FROM launch_projects p
WHERE p.id = ri.launch_project_id AND p.launch_key = {lk} AND {capture_filter('ri')}
  AND ri.review_type = 'refinement_action_review' AND ri.status = 'pending'
  AND ri.refinement_action_id IN (
    SELECT a.id FROM design_refinement_actions a
    JOIN launch_projects p2 ON p2.id = a.launch_project_id
    WHERE p2.launch_key = {lk} AND {capture_filter('a')} AND a.action_key IN ({refinements_sql()})
  );
""")

    blocks.append(f"""
DO $GUARD$
DECLARE unsafe int; ext int; se int; pe int; rf boolean; inbound int; contacts_count int;
BEGIN
  SELECT
      (SELECT count(*) FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id
         WHERE p.launch_key = {lk} AND {capture_filter('o')} AND (o.contains_private_contact_data OR o.contains_secrets))
    + (SELECT count(*) FROM design_second_opinion_reviews r JOIN launch_projects p ON p.id = r.launch_project_id
         WHERE p.launch_key = {lk} AND {capture_filter('r')} AND (r.contains_private_contact_data OR r.contains_secrets))
  INTO unsafe;
  SELECT external_call_made_count INTO ext FROM vw_dlf_design_output_readiness WHERE launch_key = {lk};
  SELECT send_enabled_count INTO se FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT publish_enabled_count INTO pe FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT ready_for_launch_push INTO rf FROM vw_dlf_launch_priority_dashboard WHERE launch_key = {lk};
  SELECT count(*) INTO inbound FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  IF unsafe > 0 THEN RAISE EXCEPTION 'Refusing: reviewed rows flagged with contact data or secrets (%).', unsafe; END IF;
  IF ext > 0 THEN RAISE EXCEPTION 'Refusing: design rows marked external_call_made (%).', ext; END IF;
  IF se > 0 OR pe > 0 THEN RAISE EXCEPTION 'Refusing: send/publish enabled (send=%, publish=%).', se, pe; END IF;
  IF rf THEN RAISE EXCEPTION 'Refusing: ready_for_launch_push would be true.'; END IF;
  IF inbound <> 0 THEN RAISE EXCEPTION 'Refusing: inbound lead count changed to %.', inbound; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
END $GUARD$;
COMMIT;

SELECT 'output_accepted_direction', count(*)::text FROM fable_design_outputs o JOIN launch_projects p ON p.id = o.launch_project_id WHERE p.launch_key = {lk} AND {capture_filter('o')} AND o.output_status = 'accepted_direction'
UNION ALL SELECT 'gemini_accepted_guidance', count(*)::text FROM design_second_opinion_reviews r JOIN launch_projects p ON p.id = r.launch_project_id WHERE p.launch_key = {lk} AND {capture_filter('r')} AND r.review_status = 'accepted_guidance'
UNION ALL SELECT 'refinement_actions_accepted', count(*)::text FROM design_refinement_actions a JOIN launch_projects p ON p.id = a.launch_project_id WHERE p.launch_key = {lk} AND {capture_filter('a')} AND a.action_status = 'accepted'
UNION ALL SELECT 'review_items_approved', count(*)::text FROM fable_design_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND {capture_filter('ri')} AND ri.status = 'approved'
UNION ALL SELECT 'review_items_pending', count(*)::text FROM fable_design_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND {capture_filter('ri')} AND ri.status = 'pending'
UNION ALL SELECT 'external_call_made_count', external_call_made_count::text FROM vw_dlf_design_output_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_fable_followup', ready_for_fable_followup::text FROM vw_dlf_design_output_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_wix_design_build', ready_for_wix_design_build::text FROM vw_dlf_design_output_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'send_enabled_count', send_enabled_count::text FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
UNION ALL SELECT 'publish_enabled_count', publish_enabled_count::text FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
UNION ALL SELECT 'ready_for_launch_push', ready_for_launch_push::text FROM vw_dlf_launch_priority_dashboard WHERE launch_key = {lk}
UNION ALL SELECT 'inbound_leads', count(*)::text FROM inbound_leads
UNION ALL SELECT 'contacts', count(*)::text FROM contacts
ORDER BY 1;
""")
    return "\n".join(blocks)

def main() -> int:
    parser = argparse.ArgumentParser(description="Approve DLF Westpark Gallery White design direction. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--reviewed-by", default=None)
    parser.add_argument("--decision-notes", default=None)
    parser.add_argument("--accept-fable-output", action="store_true")
    parser.add_argument("--accept-gemini-guidance", action="store_true")
    parser.add_argument("--accept-core-refinements", action="store_true")
    parser.add_argument("--mark-build-ready-after-review", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    # Defensive: always refused.
    parser.add_argument("--call-fable", action="store_true")
    parser.add_argument("--call-gemini", action="store_true")
    parser.add_argument("--call-wix", action="store_true")
    parser.add_argument("--enable-send", action="store_true")
    parser.add_argument("--enable-publish", action="store_true")
    parser.add_argument("--mark-ready-for-launch-push", action="store_true")
    args = parser.parse_args()

    print(f"DLF Gallery White design-direction review. launch_key={args.launch_key}. Counts only; no raw artifact contents.")

    if args.call_fable or args.call_gemini or args.call_wix:
        print("Refusing: this script never calls Fable, Gemini, or Wix APIs.")
        return 1
    if args.enable_send or args.enable_publish or args.mark_ready_for_launch_push:
        print("Refusing: this script never enables send/publish or marks ready_for_launch_push.")
        return 1

    do_output = args.accept_fable_output
    do_gemini = args.accept_gemini_guidance
    do_refine = args.accept_core_refinements
    if not (do_output or do_gemini or do_refine):
        print("Nothing to do: pass at least one of --accept-fable-output, --accept-gemini-guidance, --accept-core-refinements.")
        return 1

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 14:
        print("Refusing: probe returned no usable result (launch project may be missing).")
        return 1
    (out_total, out_accepted, out_unsafe, out_ext,
     rev_total, rev_accepted, rev_unsafe, rev_ext,
     refine_total, refine_accepted,
     pend_output, pend_gemini, pend_refine) = (int(x or 0) for x in f[:13])
    ready_build = f[13].strip() == "true"

    if out_total == 0:
        print("Refusing: no Phase 7.17 captured Fable design output found for this launch key.")
        return 1
    if out_unsafe or rev_unsafe:
        print(f"Refusing: captured rows flagged with contact data or secrets (outputs={out_unsafe}, reviews={rev_unsafe}).")
        return 1
    if out_ext or rev_ext:
        print(f"Refusing: captured rows marked external_call_made (outputs={out_ext}, reviews={rev_ext}).")
        return 1

    print("inputs (counts only):")
    print(f"  design outputs: {out_total} (already accepted: {out_accepted})   unsafe flags: {out_unsafe}   external: {out_ext}")
    print(f"  second-opinion reviews: {rev_total} (already accepted: {rev_accepted})   unsafe flags: {rev_unsafe}   external: {rev_ext}")
    print(f"  core refinement actions present: {refine_total}/12 (already accepted: {refine_accepted})")
    print(f"  pending review items — output: {pend_output}   gemini: {pend_gemini}   refinement: {pend_refine}")
    print(f"  ready_for_wix_design_build (current): {ready_build}")
    print("projected actions:")
    if do_output:
        print("  Gallery White output -> accepted_direction; fable_output_review -> approved")
    if do_gemini:
        print("  Gemini review -> accepted_guidance; gemini_review_review -> approved")
    if do_refine:
        print(f"  {refine_total} refinement actions -> accepted; refinement_action_review items -> approved")
    if args.mark_build_ready_after_review:
        print("  build_ready_acknowledged stamped on accepted output (informational; no publish/build/launch)")
    print("  Fable/Gemini/Wix/Meta/WhatsApp/email/n8n calls: 0   publishing: 0   live forms/webhooks: 0")
    print("  contacts/leads/messages changed: 0   send/publish/ready_for_launch_push: unchanged (false)")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    if not (args.reviewed_by or "").strip() or not (args.decision_notes or "").strip():
        print("Refusing: --reviewed-by and --decision-notes are required for an audited apply.")
        return 1

    code, output = run_psql(apply_sql(args.launch_key, args.reviewed_by, args.decision_notes,
                                      do_output, do_gemini, do_refine, args.mark_build_ready_after_review))
    print("Design-direction review applied:" if code == 0 else "Design-direction review FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
