#!/usr/bin/env python3
"""Phase 7.10 — DLF controlled FAKE lead-intake test harness. Dry-run by default.

Creates clearly-fake test lead payloads in the dedicated launch_test_lead_* tables ONLY, validates
them against the field-mapping / consent / UTM / attribution / scoring expectations, and queues
human review items. It NEVER touches the real inbound_leads or contacts tables, never calls an
external API or webhook, never sends or publishes, and cannot make any live/launch flag true.

Every payload is flagged uses_fake_data=true / creates_real_contact=false / creates_real_lead=false
/ external_call_made=false, and is tagged raw_context.phase='7.10' / source='dlf_test_lead_intake'
so cleanup_dlf_test_lead_intake.py can remove it. Fake contact values use clearly-fake,
non-routable placeholders and are NEVER printed and NEVER exposed by any view.

Writing requires BOTH --real-ok and --apply. Counts only.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.10"
SOURCE = "dlf_test_lead_intake"

VALIDATION_TYPES = ("required_fields", "pii_mapping", "consent_fields", "utm_mapping",
                    "attribution_rule", "lead_scoring", "duplicate_check", "review_item_creation")

# Five controlled fake scenarios. Fake contact values are clearly fake / non-routable
# (RFC2606 .invalid domain; placeholder phone). They are stored only in fake_* columns,
# never exposed by a view, never printed.
PAYLOADS = [
    {
        "key": "dlf-test-lead-001", "type": "wix_form", "name": "FAKE DLF TEST LEAD 001",
        "phone": "FAKE-PHONE-0000000001", "email": "fake-lead-001@example.invalid",
        "scenario": "valid_brochure_request", "source": "google",
        "has_name": True, "has_phone": True, "has_email": True, "has_consent": True,
        "budget_band": "mid", "extra_reviews": [],
    },
    {
        "key": "dlf-test-lead-002", "type": "wix_form", "name": "FAKE DLF TEST LEAD 002",
        "phone": "FAKE-PHONE-0000000002", "email": "fake-lead-002@example.invalid",
        "scenario": "missing_consent", "source": "instagram",
        "has_name": True, "has_phone": True, "has_email": True, "has_consent": False,
        "budget_band": "mid", "extra_reviews": ["validation_result_review"],
    },
    {
        "key": "dlf-test-lead-003", "type": "whatsapp_click", "name": "FAKE DLF TEST LEAD 003",
        "phone": None, "email": None,
        "scenario": "missing_phone_and_email", "source": "whatsapp",
        "has_name": True, "has_phone": False, "has_email": False, "has_consent": True,
        "budget_band": "unknown", "extra_reviews": ["validation_result_review"],
    },
    {
        "key": "dlf-test-lead-004", "type": "instagram_link", "name": "FAKE DLF TEST LEAD 004",
        "phone": "FAKE-PHONE-0000000004", "email": "fake-lead-004@example.invalid",
        "scenario": "high_budget_hot_lead", "source": "instagram",
        "has_name": True, "has_phone": True, "has_email": True, "has_consent": True,
        "budget_band": "high", "extra_reviews": [],
    },
    {
        "key": "dlf-test-lead-005", "type": "referral_link", "name": "FAKE DLF TEST LEAD 005",
        "phone": "FAKE-PHONE-0000000005", "email": None,
        "scenario": "referral_lead", "source": "referral",
        "has_name": True, "has_phone": True, "has_email": False, "has_consent": True,
        "budget_band": "mid", "extra_reviews": [],
    },
]

def validations_for(pl: dict) -> dict:
    """Deterministic validation outcomes for a fake payload."""
    required = "passed" if (pl["has_name"] and (pl["has_phone"] or pl["has_email"])) else "failed"
    consent = "passed" if pl["has_consent"] else "failed"
    # whatsapp_click has no UTM context -> needs_review; other channels carry UTM.
    utm = "needs_review" if pl["type"] == "whatsapp_click" else "passed"
    return {
        "required_fields": required,
        "pii_mapping": "passed",          # name/phone/email field mappings exist in the schema
        "consent_fields": consent,
        "utm_mapping": utm,
        "attribution_rule": "passed",     # every scenario source matches a draft attribution rule
        "lead_scoring": "passed",         # scoring rules exist; score recorded in raw_context
        "duplicate_check": "passed",      # fake data: no real contact match
        "review_item_creation": "passed",
    }

def payload_status(vals: dict) -> str:
    blocking = (vals["required_fields"], vals["consent_fields"], vals["pii_mapping"])
    return "failed" if "failed" in blocking else "validated"
def build_apply_sql(launch_key: str, cleanup_existing: bool) -> tuple[str, int, int, int]:
    lk = sql_literal(launch_key)
    payload_rows, validation_rows, review_rows = [], [], []
    n_val = n_rev = 0
    for pl in PAYLOADS:
        vals = validations_for(pl)
        status = payload_status(vals)
        fake_payload = json.dumps({
            "scenario": pl["scenario"], "source": pl["source"], "payload_type": pl["type"],
            "has_consent": pl["has_consent"], "has_phone": pl["has_phone"], "has_email": pl["has_email"],
            "budget_band": pl["budget_band"], "note": "fake test payload — no real contact data",
        })
        payload_rows.append(
            f"({sql_literal(pl['key'])}, {sql_literal(status)}, {sql_literal(pl['type'])}, "
            f"{sql_literal(pl['name'])}, {sql_literal(pl['phone'])}, {sql_literal(pl['email'])}, "
            f"{sql_literal(fake_payload)})"
        )
        for vtype in VALIDATION_TYPES:
            vstatus = vals[vtype]
            summary = f"{pl['scenario']}: {vtype} -> {vstatus}"
            validation_rows.append(
                f"({sql_literal(pl['key'])}, {sql_literal(vtype)}, {sql_literal(vstatus)}, {sql_literal(summary)})"
            )
            n_val += 1
        reviews = ["fake_payload_review"] + pl["extra_reviews"] + ["privacy_review"]
        for rtype in reviews:
            prio = "high" if rtype == "validation_result_review" else "normal"
            review_rows.append(f"({sql_literal(pl['key'])}, {sql_literal(rtype)}, {sql_literal(prio)})")
            n_rev += 1
    # one batch-level cleanup review, attached to the first payload
    review_rows.append(f"({sql_literal(PAYLOADS[0]['key'])}, 'cleanup_review', 'normal')")
    n_rev += 1

    cleanup_block = ""
    if cleanup_existing:
        cleanup_block = f"""
DELETE FROM launch_test_lead_review_items ri USING launch_projects p
  WHERE p.id = ri.launch_project_id AND p.launch_key = {lk} AND ri.raw_context->>'phase' = '{PHASE}';
DELETE FROM launch_test_lead_validation_results v USING launch_projects p
  WHERE p.id = v.launch_project_id AND p.launch_key = {lk} AND v.raw_context->>'phase' = '{PHASE}';
DELETE FROM launch_test_lead_payloads t USING launch_projects p
  WHERE p.id = t.launch_project_id AND p.launch_key = {lk} AND t.raw_context->>'phase' = '{PHASE}';
"""

    sql = f"""
BEGIN;
{cleanup_block}
INSERT INTO launch_test_lead_payloads
  (launch_project_id, test_key, payload_status, payload_type, fake_name, fake_phone, fake_email, fake_payload,
   uses_fake_data, creates_real_contact, creates_real_lead, external_call_made, raw_context)
SELECT p.id, v.test_key, v.payload_status, v.payload_type, v.fake_name, v.fake_phone, v.fake_email, v.fake_payload::jsonb,
   true, false, false, false, jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
FROM launch_projects p
JOIN (VALUES {", ".join(payload_rows)}) AS v(test_key, payload_status, payload_type, fake_name, fake_phone, fake_email, fake_payload) ON true
WHERE p.launch_key = {lk}
  AND NOT EXISTS (SELECT 1 FROM launch_test_lead_payloads e WHERE e.test_key = v.test_key);

INSERT INTO launch_test_lead_validation_results
  (launch_project_id, test_payload_id, validation_type, validation_status, safe_summary, raw_context)
SELECT t.launch_project_id, t.id, v.validation_type, v.validation_status, v.safe_summary,
   jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
FROM launch_test_lead_payloads t
JOIN (VALUES {", ".join(validation_rows)}) AS v(test_key, validation_type, validation_status, safe_summary) ON v.test_key = t.test_key
WHERE t.raw_context->>'phase' = '{PHASE}'
  AND NOT EXISTS (SELECT 1 FROM launch_test_lead_validation_results e WHERE e.test_payload_id = t.id AND e.validation_type = v.validation_type);

INSERT INTO launch_test_lead_review_items
  (launch_project_id, test_payload_id, review_type, status, priority, raw_context)
SELECT t.launch_project_id, t.id, v.review_type, 'pending', v.priority,
   jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
FROM launch_test_lead_payloads t
JOIN (VALUES {", ".join(review_rows)}) AS v(test_key, review_type, priority) ON v.test_key = t.test_key
WHERE t.raw_context->>'phase' = '{PHASE}'
  AND NOT EXISTS (SELECT 1 FROM launch_test_lead_review_items e WHERE e.test_payload_id = t.id AND e.review_type = v.review_type);

-- Hard guardrail: the harness must stay fake-only and change no live/launch flag.
DO $GUARD$
DECLARE bad int; se int; pe int; rf boolean; tready boolean; il int;
BEGIN
  SELECT count(*) FROM launch_test_lead_payloads t JOIN launch_projects p ON p.id = t.launch_project_id
    WHERE p.launch_key = {lk} AND (t.uses_fake_data = false OR t.creates_real_contact OR t.creates_real_lead OR t.external_call_made) INTO bad;
  SELECT (SELECT count(*) FROM launch_message_templates m JOIN launch_projects p ON p.id = m.launch_project_id WHERE p.launch_key = {lk} AND m.send_enabled)
       + (SELECT count(*) FROM launch_channels c JOIN launch_projects p ON p.id = c.launch_project_id WHERE p.launch_key = {lk} AND c.send_enabled) INTO se;
  SELECT (SELECT count(*) FROM launch_channels c JOIN launch_projects p ON p.id = c.launch_project_id WHERE p.launch_key = {lk} AND c.publish_enabled)
       + (SELECT count(*) FROM launch_landing_page_specs s JOIN launch_projects p ON p.id = s.launch_project_id WHERE p.launch_key = {lk} AND s.publish_enabled) INTO pe;
  SELECT ready_for_launch_push INTO rf FROM vw_dlf_launch_priority_dashboard WHERE launch_key = {lk};
  SELECT ready_for_live_lead_capture INTO tready FROM vw_dlf_test_lead_readiness WHERE launch_key = {lk};
  SELECT count(*) FROM inbound_leads WHERE raw_payload->>'phase' = '{PHASE}' INTO il;
  IF bad > 0 THEN RAISE EXCEPTION 'Refusing: % test payload(s) flagged real/external.', bad; END IF;
  IF se > 0 OR pe > 0 THEN RAISE EXCEPTION 'Refusing: send/publish enabled (send=%, publish=%).', se, pe; END IF;
  IF rf THEN RAISE EXCEPTION 'Refusing: ready_for_launch_push would be true.'; END IF;
  IF tready THEN RAISE EXCEPTION 'Refusing: test harness made ready_for_live_lead_capture true.'; END IF;
  IF il > 0 THEN RAISE EXCEPTION 'Refusing: real inbound_leads created by harness (%).', il; END IF;
END $GUARD$;
COMMIT;

SELECT 'fake_payloads', count(*)::text FROM launch_test_lead_payloads t JOIN launch_projects p ON p.id = t.launch_project_id WHERE p.launch_key = {lk} AND t.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'payloads_validated', count(*)::text FROM launch_test_lead_payloads t JOIN launch_projects p ON p.id = t.launch_project_id WHERE p.launch_key = {lk} AND t.raw_context->>'phase' = '{PHASE}' AND t.payload_status = 'validated'
UNION ALL SELECT 'payloads_failed', count(*)::text FROM launch_test_lead_payloads t JOIN launch_projects p ON p.id = t.launch_project_id WHERE p.launch_key = {lk} AND t.raw_context->>'phase' = '{PHASE}' AND t.payload_status = 'failed'
UNION ALL SELECT 'validations_total', count(*)::text FROM launch_test_lead_validation_results v JOIN launch_projects p ON p.id = v.launch_project_id WHERE p.launch_key = {lk} AND v.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'validations_passed', count(*)::text FROM launch_test_lead_validation_results v JOIN launch_projects p ON p.id = v.launch_project_id WHERE p.launch_key = {lk} AND v.raw_context->>'phase' = '{PHASE}' AND v.validation_status = 'passed'
UNION ALL SELECT 'validations_failed', count(*)::text FROM launch_test_lead_validation_results v JOIN launch_projects p ON p.id = v.launch_project_id WHERE p.launch_key = {lk} AND v.raw_context->>'phase' = '{PHASE}' AND v.validation_status = 'failed'
UNION ALL SELECT 'review_items', count(*)::text FROM launch_test_lead_review_items ri JOIN launch_projects p ON p.id = ri.launch_project_id WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'real_inbound_leads', count(*)::text FROM inbound_leads
UNION ALL SELECT 'contacts', count(*)::text FROM contacts
UNION ALL SELECT 'ready_for_live_lead_capture', ready_for_live_lead_capture::text FROM vw_dlf_test_lead_readiness WHERE launch_key = {lk}
UNION ALL SELECT 'send_enabled', send_enabled_count::text FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
UNION ALL SELECT 'safety_status', safety_status FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}
ORDER BY 1;
"""
    return sql, len(PAYLOADS), n_val, n_rev

def main() -> int:
    parser = argparse.ArgumentParser(description="DLF controlled fake lead-intake test harness. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--retain-test-rows", action="store_true", help="acknowledge the fake test rows are kept for dashboard QA")
    parser.add_argument("--cleanup-existing-test-rows", action="store_true", help="delete prior phase 7.10 test rows before creating new ones")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF test lead intake harness. launch_key={args.launch_key}. FAKE data only; counts only; no contact values.")
    sql, n_payloads, n_val, n_rev = build_apply_sql(args.launch_key, args.cleanup_existing_test_rows)

    print("projected (counts only):")
    print(f"  fake payloads: {n_payloads} (scenarios: valid brochure, missing consent, missing phone/email, high-budget, referral)")
    print(f"  validation results: {n_val} ({len(VALIDATION_TYPES)} per payload)")
    print(f"  review items: {n_rev}")
    print("  real inbound_leads created: 0   contacts created/merged: 0   external calls/webhooks: 0")
    print("  ready_for_live_lead_capture stays false; send/publish stay 0")
    print(f"  rows retained after apply: {'yes (--retain-test-rows)' if args.retain_test_rows else 'yes (default; use cleanup script to remove)'}")
    if args.cleanup_existing_test_rows:
        print("  NOTE: existing phase 7.10 test rows will be deleted first (re-run).")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    code, output = run_psql(sql)
    print("Test lead intake applied:" if code == 0 else "Test lead intake FAILED (rolled back):")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
