#!/usr/bin/env python3
"""Phase 7.3: seed the DLF lead-intake and attribution plan.

Creates inert planning rows only: planned endpoints, draft field mappings, draft
attribution rules copied from Phase 7.1 UTM specs, 30 zero-valued daily metric
placeholders, and readiness checks. No Wix/n8n APIs, no live webhooks, no inbound
leads, no contacts, no sends, no publishing. Dry-run by default; --real-ok is
required; --apply writes.
"""

from __future__ import annotations
from _db import jsonb_lit, read_env_value, run_psql, scalar, sql_literal

import argparse
import datetime as dt
import json
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.3"
SOURCE = "dlf_lead_intake_plan_seed"
BASE_TAG = {
    "phase": PHASE,
    "source": SOURCE,
    "external_calls_made": False,
    "external_call_allowed": False,
    "communication_sent": False,
    "published": False,
}
PHASE_TABLES = [
    "launch_lead_intake_endpoints",
    "launch_lead_field_mappings",
    "launch_lead_attribution_rules",
    "launch_operator_daily_metrics",
    "launch_readiness_checks",
]

ENDPOINTS = [
    ("wix_landing_page_form", "wix_form", "wix", "dlf-westend-lead-form", True, "Wix form endpoint planned; not live."),
    ("n8n_wix_lead_webhook", "n8n_webhook", "n8n", "dlf-westend-lead-form", True, "n8n webhook path planned; not created."),
    ("instagram_bio_link", "instagram_link", "instagram", None, False, "UTM link target planned."),
    ("youtube_shorts_link", "youtube_link", "youtube_shorts", None, False, "UTM link target planned."),
    ("whatsapp_click_to_chat", "whatsapp_click", "whatsapp", None, False, "Click-to-chat source planned; not sending."),
    ("email_campaign_link", "email_link", "email", None, False, "Email link attribution planned; no email send."),
    ("referral_link", "referral_link", "referral", None, False, "Referral link attribution planned."),
    ("listing_portal_manual_entry", "manual_entry", "listing_portal", None, False, "Manual listing-portal entry plan."),
]

FIELD_MAPPINGS = [
    ("name", "Name", "inbound_leads", "lead_name_masked", "text", True, "name", "mask_before_storage"),
    ("phone", "Phone", "inbound_leads", "raw_payload.phone", "phone", True, "phone", "validate_and_review_before_contact"),
    ("email", "Email", "inbound_leads", "raw_payload.email", "email", False, "email", "validate_and_review_before_contact"),
    ("interested_configuration", "Interested configuration", "inbound_leads", "raw_payload.interested_configuration", "select", False, "preference", "operator_review"),
    ("budget_range", "Budget range", "inbound_leads", "budget_min/budget_max", "select", False, "budget", "operator_review"),
    ("buying_purpose", "Buying purpose", "inbound_leads", "lead_intent", "select", False, "preference", "operator_review"),
    ("timeframe", "Timeframe", "inbound_leads", "raw_payload.timeframe", "select", False, "preference", "operator_review"),
    ("location_preference", "Location preference", "inbound_leads", "area", "text", False, "preference", "operator_review"),
    ("site_visit_interest", "Site visit interest", "inbound_leads", "raw_payload.site_visit_interest", "consent", False, "preference", "operator_review"),
    ("brochure_requested", "Brochure requested", "inbound_leads", "raw_payload.brochure_requested", "consent", False, "preference", "operator_review"),
    ("whatsapp_optin", "WhatsApp opt-in", "channel_permissions", "permission_status", "consent", True, "consent", "explicit_true_required"),
    ("email_optin", "Email opt-in", "channel_permissions", "permission_status", "consent", False, "consent", "explicit_true_required"),
    ("source", "Source", "inbound_leads", "source_id", "hidden_utm", False, "none", "known_source_only"),
    ("utm_source", "UTM source", "lead_attribution_events", "utm_source", "hidden_utm", False, "none", "known_utm_or_blank"),
    ("utm_medium", "UTM medium", "lead_attribution_events", "utm_medium", "hidden_utm", False, "none", "known_utm_or_blank"),
    ("utm_campaign", "UTM campaign", "lead_attribution_events", "utm_campaign", "hidden_utm", False, "none", "known_utm_or_blank"),
    ("utm_content", "UTM content", "lead_attribution_events", "raw_context.utm_content", "hidden_utm", False, "none", "known_utm_or_blank"),
    ("landing_page_slug", "Landing page slug", "lead_attribution_events", "landing_page", "hidden_utm", False, "none", "known_page_only"),
]

READINESS_CHECKS = [
    ("wix_form_fields_reviewed", "high", "Wix form field mapping requires human review."),
    ("n8n_webhook_planned", "high", "n8n webhook plan exists but is not live."),
    ("attribution_rules_reviewed", "normal", "UTM attribution rules require human review."),
    ("lead_privacy_reviewed", "blocker", "Lead privacy and consent handling require review."),
    ("lead_duplicate_review_ready", "high", "Duplicate review queue must be ready before conversion."),
]
def tag(extra: dict | None = None) -> str:
    obj = dict(BASE_TAG)
    if extra:
        obj.update(extra)
    return jsonb_lit(obj)
def count_tagged(table: str, launch_key: str) -> int:
    out = scalar(
        f"SELECT count(*) FROM {table} t JOIN launch_projects p ON p.id = t.launch_project_id "
        f"WHERE p.launch_key = {sql_literal(launch_key)} "
        f"AND t.raw_context->>'phase' = {sql_literal(PHASE)} "
        f"AND t.raw_context->>'source' = {sql_literal(SOURCE)};"
    )
    return int(out or 0)

def utm_count(launch_key: str) -> int:
    out = scalar(
        "SELECT count(*) FROM launch_utm_campaign_specs u "
        "JOIN launch_projects p ON p.id = u.launch_project_id "
        f"WHERE p.launch_key = {sql_literal(launch_key)};"
    )
    return int(out or 0)

def priority_for_source(source: str) -> int:
    order = {
        "google": 80,
        "instagram": 70,
        "youtube": 65,
        "whatsapp": 60,
        "email": 55,
        "referral": 50,
        "listing_portal": 45,
        "blog": 40,
    }
    return order.get(source, 10)

def main() -> int:
    parser = argparse.ArgumentParser(description="Seed DLF lead-intake plan. Counts only.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-existing", action="store_true")
    args = parser.parse_args()

    if not args.real_ok:
        print("Refusing: --real-ok is required (even for dry-run).")
        return 1

    code, project_out = run_psql(
        f"SELECT id FROM launch_projects WHERE launch_key = {sql_literal(args.launch_key)};"
    )
    if code != 0:
        print(project_out)
        return code
    if not project_out:
        print(f"Refusing: launch project not found for launch_key={args.launch_key!r}.")
        return 1
    project_id = project_out.splitlines()[0]

    form_out = scalar(
        "SELECT id FROM launch_lead_capture_forms "
        f"WHERE launch_project_id = {sql_literal(project_id)} "
        "ORDER BY created_at, form_key LIMIT 1;"
    )
    if not form_out:
        print("Refusing: no lead capture form exists for this launch. Run Phase 7.1 first.")
        return 1
    lead_capture_form_id = form_out

    existing = sum(count_tagged(table, args.launch_key) for table in PHASE_TABLES)
    if existing and not args.allow_existing:
        print(f"Refusing: {existing} Phase 7.3 row(s) already exist. Use --allow-existing to add more.")
        return 1

    utms = utm_count(args.launch_key)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== Phase 7.3 DLF lead-intake plan seed [{mode}] ===")
    print(f"launch_key={args.launch_key}")
    print(f"  endpoints_planned={len(ENDPOINTS)}")
    print(f"  field_mappings_draft={len(FIELD_MAPPINGS)}")
    print(f"  attribution_rules_draft={utms}")
    print("  inbound_lead_review_items=0")
    print("  daily_metric_placeholders=30")
    print(f"  readiness_checks_if_missing={len(READINESS_CHECKS)}")
    print("external_call_allowed=0  live_webhooks=0  inbound_leads_created=0  contacts_created=0  messages_sent=0")

    if not args.apply:
        print("DRY-RUN only: no DB writes. Re-run with --apply to seed.")
        return 0

    today = dt.date.today()
    sql = ["BEGIN;"]
    for endpoint_key, endpoint_type, channel, form_key, requires_call, note in ENDPOINTS:
        planned_url = None
        webhook_path = None
        if endpoint_key == "wix_landing_page_form":
            planned_url = "/dlf-westend-andheri-west"
        if endpoint_key == "n8n_wix_lead_webhook":
            webhook_path = "/webhook/dlf/wix-lead-intake-planned"
        sql.append(
            "INSERT INTO launch_lead_intake_endpoints (id, launch_project_id, endpoint_key, endpoint_type, "
            "endpoint_status, planned_url, webhook_path, source_channel, form_key, external_call_required, "
            "external_call_allowed, human_review_required, raw_context) VALUES ("
            f"{sql_literal(str(uuid.uuid4()))}, {sql_literal(project_id)}, {sql_literal(endpoint_key)}, "
            f"{sql_literal(endpoint_type)}, 'planned', {sql_literal(planned_url)}, {sql_literal(webhook_path)}, "
            f"{sql_literal(channel)}, {sql_literal(form_key)}, {'true' if requires_call else 'false'}, "
            f"false, true, {tag({'safe_summary': note})});"
        )

    for field_key, label, target_table, target_field, field_type, required, pii_type, validation in FIELD_MAPPINGS:
        sql.append(
            "INSERT INTO launch_lead_field_mappings (id, launch_project_id, lead_capture_form_id, field_key, "
            "field_label, target_table, target_field, field_type, required, pii_type, validation_rule, "
            "mapping_status, raw_context) VALUES ("
            f"{sql_literal(str(uuid.uuid4()))}, {sql_literal(project_id)}, {sql_literal(lead_capture_form_id)}, "
            f"{sql_literal(field_key)}, {sql_literal(label)}, {sql_literal(target_table)}, {sql_literal(target_field)}, "
            f"{sql_literal(field_type)}, {'true' if required else 'false'}, {sql_literal(pii_type)}, "
            f"{sql_literal(validation)}, 'draft', {tag()});"
        )

    code, utm_rows = run_psql(
        "SELECT channel, campaign_name, source, medium, content_angle, funnel_stage "
        "FROM launch_utm_campaign_specs "
        f"WHERE launch_project_id = {sql_literal(project_id)} ORDER BY channel, campaign_name;"
    )
    if code != 0:
        print(utm_rows)
        return code
    for line in filter(None, utm_rows.splitlines()):
        channel, campaign_name, source, medium, content_angle, funnel_stage = (line.split("|") + [""] * 6)[:6]
        rule_key = f"{channel}_{source}_{medium}_{funnel_stage}".replace(" ", "_").lower()
        segment_key = "inbound_new_lead_review"
        if source == "referral":
            segment_key = "owner_network_referrals"
        elif source in ("instagram", "youtube"):
            segment_key = "social_launch_interest"
        elif source == "google":
            segment_key = "seo_launch_interest"
        sql.append(
            "INSERT INTO launch_lead_attribution_rules (id, launch_project_id, rule_key, source, medium, "
            "campaign_name, content_angle, mapped_channel, mapped_funnel_stage, mapped_segment_key, priority, "
            "rule_status, raw_context) VALUES ("
            f"{sql_literal(str(uuid.uuid4()))}, {sql_literal(project_id)}, {sql_literal(rule_key)}, "
            f"{sql_literal(source)}, {sql_literal(medium)}, {sql_literal(campaign_name)}, "
            f"{sql_literal(content_angle)}, {sql_literal(channel)}, {sql_literal(funnel_stage)}, "
            f"{sql_literal(segment_key)}, {priority_for_source(source)}, 'draft', {tag()});"
        )

    for offset in range(30):
        metric_date = today + dt.timedelta(days=offset)
        sql.append(
            "INSERT INTO launch_operator_daily_metrics (id, launch_project_id, metric_date, notes, raw_context) "
            f"VALUES ({sql_literal(str(uuid.uuid4()))}, {sql_literal(project_id)}, "
            f"{sql_literal(metric_date.isoformat())}, 'Phase 7.3 placeholder; zero metrics until live intake is approved.', {tag()});"
        )

    for check_type, severity, summary in READINESS_CHECKS:
        sql.append(
            "INSERT INTO launch_readiness_checks (launch_project_id, check_type, check_status, severity, "
            "safe_summary, raw_context) "
            f"SELECT {sql_literal(project_id)}, {sql_literal(check_type)}, 'pending', {sql_literal(severity)}, "
            f"{sql_literal(summary)}, {tag()} "
            "WHERE NOT EXISTS (SELECT 1 FROM launch_readiness_checks "
            f"WHERE launch_project_id = {sql_literal(project_id)} AND check_type = {sql_literal(check_type)});"
        )

    sql.append("COMMIT;")
    code, out = run_psql("\n".join(sql))
    if code != 0:
        print(f"DB write FAILED (rolled back): {out[:400]}")
        return 2
    print("APPLIED: Phase 7.3 lead-intake plan seeded. No inbound leads, contacts, sends, publishing, live webhooks, or external API calls.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
