#!/usr/bin/env python3
"""Phase 7.4: seed DLF n8n workflow blueprints.

Creates planned n8n workflow blueprints, nodes, one draft payload schema, fake-only
test cases, and review items. No n8n API calls, live workflows, webhooks, inbound
leads, contacts, messages, or publishing. Dry-run by default; --real-ok required;
--apply writes.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.4"
SOURCE = "dlf_n8n_workflow_blueprint_seed"
BASE_TAG = {
    "phase": PHASE,
    "source": SOURCE,
    "external_calls_made": False,
    "external_call_allowed": False,
    "workflow_created_in_n8n": False,
    "activation_requested": False,
    "communication_sent": False,
}
PHASE_TABLES = [
    "launch_n8n_workflow_blueprints",
    "launch_n8n_workflow_nodes",
    "launch_n8n_payload_schemas",
    "launch_n8n_test_cases",
    "launch_n8n_review_items",
]

BLUEPRINTS = [
    ("wix_lead_intake_webhook", "Wix lead intake webhook", "lead_intake", True),
    ("lead_payload_validation", "Lead payload validation", "lead_validation", False),
    ("lead_attribution_and_scoring", "Lead attribution and scoring", "attribution", False),
    ("operator_review_task_creation", "Operator review task creation", "followup_task_creation", False),
    ("duplicate_contact_check", "Duplicate contact check", "lead_validation", False),
    ("error_handling_and_dead_letter", "Error handling and dead letter", "error_handling", False),
]

NODES = {
    "wix_lead_intake_webhook": [
        ("webhook_trigger", "webhook_trigger", 10, "Incoming form metadata only", "Payload passed to validation", "Reject malformed request and stop."),
        ("normalize_lead_payload", "normalize_lead", 20, "Webhook payload", "Normalized field envelope", "Route to error handler."),
        ("route_to_validation", "validate_payload", 30, "Normalized envelope", "Validation workflow handoff", "Create review item for invalid envelope."),
    ],
    "lead_payload_validation": [
        ("required_field_check", "validate_payload", 10, "Normalized envelope", "Required-field result", "Reject to operator review."),
        ("consent_check", "validate_payload", 20, "Consent flags", "Consent result", "Mark needs consent review."),
        ("pii_masking_plan", "normalize_lead", 30, "PII fields", "Masked lead hint plan", "Block storage until reviewed."),
        ("validation_decision", "validate_payload", 40, "Validation results", "Pass/fail routing", "Route failures to dead letter."),
    ],
    "lead_attribution_and_scoring": [
        ("utm_parser", "utm_parser", 10, "UTM fields", "Attribution metadata", "Keep unknown UTM as needs review."),
        ("insert_inbound_lead_plan", "insert_inbound_lead", 20, "Validated lead", "Planned inbound lead insert", "Do not insert in Phase 7.4."),
        ("create_attribution_event_plan", "create_attribution_event", 30, "Attribution metadata", "Planned event insert", "Do not insert in Phase 7.4."),
        ("lead_score_plan", "lead_score", 40, "Mapped lead signals", "Draft score result", "Default to review queue."),
    ],
    "operator_review_task_creation": [
        ("create_review_item_plan", "create_review_item", 10, "Validated/scored lead", "Operator review item plan", "Create no real review item in Phase 7.4."),
        ("assign_operator_queue", "create_review_item", 20, "Review priority", "Queue assignment plan", "Leave unassigned if rules fail."),
        ("notify_operator_plan", "notify_operator", 30, "Review item metadata", "Internal notification plan", "No notification sent in Phase 7.4."),
    ],
    "duplicate_contact_check": [
        ("phone_email_duplicate_check", "duplicate_check", 10, "Masked/normalized contact keys", "Potential duplicate result", "Operator review before conversion."),
        ("existing_contact_match_plan", "duplicate_check", 20, "Candidate duplicate result", "Contact match review plan", "Never merge automatically."),
        ("duplicate_decision_gate", "duplicate_check", 30, "Review decision", "Conversion gate", "Block conversion on uncertainty."),
    ],
    "error_handling_and_dead_letter": [
        ("error_classifier", "error_handler", 10, "Workflow error", "Error class", "Classify and stop."),
        ("dead_letter_plan", "error_handler", 20, "Rejected payload summary", "Dead-letter review plan", "No raw payload exposed in dashboard."),
        ("retry_policy_plan", "error_handler", 30, "Recoverable error", "Retry policy plan", "Manual review before retry."),
    ],
}

PAYLOAD_SCHEMA = {
    "required_fields": ["name", "phone_or_email", "consent_flags", "source", "landing_page_slug"],
    "optional_fields": ["budget", "configuration", "timeframe", "site_visit_interest", "message"],
    "pii_fields": ["name", "phone", "email"],
    "consent_fields": ["whatsapp_optin", "email_optin"],
    "utm_fields": ["utm_source", "utm_medium", "utm_campaign", "utm_content"],
    "validation_rules": [
        "name_required_but_mask_before_dashboard",
        "phone_or_email_required",
        "whatsapp_or_email_consent_required_for_followup",
        "source_required",
        "landing_page_slug_required",
        "utm_fields_optional_but_preserved_if_present",
        "reject_unknown_large_payloads",
    ],
}

TEST_CASES = [
    ("valid_brochure_request", "Fake valid brochure request with consent and UTM metadata.", "Pass validation; create planned review path."),
    ("missing_consent", "Fake lead missing channel opt-in flags.", "Fail consent gate; create consent review path."),
    ("duplicate_phone_email", "Fake lead matching an existing masked method key.", "Route to duplicate review before conversion."),
    ("missing_phone_email", "Fake lead without phone or email.", "Fail required contact method validation."),
    ("high_budget_hot_lead", "Fake high-budget lead with site visit interest.", "Score as hot but keep human review required."),
    ("referral_lead", "Fake referral-sourced lead.", "Map to referral attribution and operator review."),
    ("bad_payload", "Fake malformed payload summary.", "Route to dead-letter/error review path."),
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


def jsonb_lit(obj) -> str:
    return sql_literal(json.dumps(obj, sort_keys=True)) + "::jsonb"


def tag(extra: dict | None = None) -> str:
    obj = dict(BASE_TAG)
    if extra:
        obj.update(extra)
    return jsonb_lit(obj)


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


def scalar(sql: str) -> str:
    code, out = run_psql(sql)
    if code != 0:
        raise RuntimeError(out)
    return out.splitlines()[0] if out else ""


def count_tagged(table: str, launch_key: str) -> int:
    out = scalar(
        f"SELECT count(*) FROM {table} t "
        f"{'JOIN launch_projects p ON p.id = t.launch_project_id' if table in ('launch_n8n_workflow_blueprints', 'launch_n8n_review_items') else 'JOIN launch_n8n_workflow_blueprints b ON b.id = t.workflow_blueprint_id JOIN launch_projects p ON p.id = b.launch_project_id'} "
        f"WHERE p.launch_key = {sql_literal(launch_key)} "
        f"AND t.raw_context->>'phase' = {sql_literal(PHASE)} "
        f"AND t.raw_context->>'source' = {sql_literal(SOURCE)};"
    )
    return int(out or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed DLF n8n workflow blueprints. Counts only.")
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

    existing = sum(count_tagged(table, args.launch_key) for table in PHASE_TABLES)
    if existing and not args.allow_existing:
        print(f"Refusing: {existing} Phase 7.4 row(s) already exist. Use --allow-existing to add more.")
        return 1

    node_count = sum(len(nodes) for nodes in NODES.values())
    review_count = len(BLUEPRINTS) + 5 + len(TEST_CASES)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== Phase 7.4 DLF n8n workflow blueprint seed [{mode}] ===")
    print(f"launch_key={args.launch_key}")
    print(f"  workflow_blueprints_planned={len(BLUEPRINTS)}")
    print(f"  workflow_nodes_planned={node_count}")
    print("  payload_schemas_draft=1")
    print(f"  fake_test_cases_draft={len(TEST_CASES)}")
    print(f"  review_items_pending={review_count}")
    print("workflow_created_in_n8n=0  active_workflows=0  external_call_allowed=0  creates_real_lead=0  inbound_leads_created=0  contacts_created=0  messages_sent=0")

    if not args.apply:
        print("DRY-RUN only: no DB writes. Re-run with --apply to seed.")
        return 0

    sql = ["BEGIN;"]
    blueprint_ids: dict[str, str] = {}
    for workflow_key, workflow_name, workflow_type, external_required in BLUEPRINTS:
        bid = str(uuid.uuid4())
        blueprint_ids[workflow_key] = bid
        sql.append(
            "INSERT INTO launch_n8n_workflow_blueprints (id, launch_project_id, workflow_key, workflow_name, "
            "workflow_type, workflow_status, n8n_workflow_id, activation_status, external_call_required, "
            "external_call_allowed, human_review_required, raw_context) VALUES ("
            f"{sql_literal(bid)}, {sql_literal(project_id)}, {sql_literal(workflow_key)}, "
            f"{sql_literal(workflow_name)}, {sql_literal(workflow_type)}, 'planned', NULL, 'not_created', "
            f"{'true' if external_required else 'false'}, false, true, {tag()});"
        )

    node_ids: list[tuple[str, str]] = []
    for workflow_key, nodes in NODES.items():
        for node_key, node_type, order, input_summary, output_summary, failure in nodes:
            nid = str(uuid.uuid4())
            node_ids.append((workflow_key, nid))
            sql.append(
                "INSERT INTO launch_n8n_workflow_nodes (id, workflow_blueprint_id, node_key, node_type, "
                "node_order, node_status, input_summary, output_summary, failure_behavior, "
                "human_review_required, raw_context) VALUES ("
                f"{sql_literal(nid)}, {sql_literal(blueprint_ids[workflow_key])}, {sql_literal(node_key)}, "
                f"{sql_literal(node_type)}, {order}, 'planned', {sql_literal(input_summary)}, "
                f"{sql_literal(output_summary)}, {sql_literal(failure)}, true, {tag()});"
            )

    lead_intake_id = blueprint_ids["wix_lead_intake_webhook"]
    schema_id = str(uuid.uuid4())
    sql.append(
        "INSERT INTO launch_n8n_payload_schemas (id, workflow_blueprint_id, schema_key, schema_status, "
        "required_fields, optional_fields, pii_fields, consent_fields, utm_fields, validation_rules, raw_context) VALUES ("
        f"{sql_literal(schema_id)}, {sql_literal(lead_intake_id)}, 'dlf_lead_intake_payload_v1', 'draft', "
        f"{jsonb_lit(PAYLOAD_SCHEMA['required_fields'])}, {jsonb_lit(PAYLOAD_SCHEMA['optional_fields'])}, "
        f"{jsonb_lit(PAYLOAD_SCHEMA['pii_fields'])}, {jsonb_lit(PAYLOAD_SCHEMA['consent_fields'])}, "
        f"{jsonb_lit(PAYLOAD_SCHEMA['utm_fields'])}, {jsonb_lit(PAYLOAD_SCHEMA['validation_rules'])}, {tag()});"
    )

    test_ids: list[str] = []
    for test_key, payload_summary, expected in TEST_CASES:
        tid = str(uuid.uuid4())
        test_ids.append(tid)
        sql.append(
            "INSERT INTO launch_n8n_test_cases (id, workflow_blueprint_id, test_key, test_status, "
            "fake_payload_summary, expected_result, uses_fake_data, creates_real_lead, external_call_allowed, raw_context) VALUES ("
            f"{sql_literal(tid)}, {sql_literal(lead_intake_id)}, {sql_literal(test_key)}, 'draft', "
            f"{sql_literal(payload_summary)}, {sql_literal(expected)}, true, false, false, {tag()});"
        )

    for workflow_key, bid in blueprint_ids.items():
        priority = "high" if workflow_key in ("wix_lead_intake_webhook", "error_handling_and_dead_letter") else "normal"
        sql.append(
            "INSERT INTO launch_n8n_review_items (launch_project_id, workflow_blueprint_id, review_type, status, priority, raw_context) "
            f"VALUES ({sql_literal(project_id)}, {sql_literal(bid)}, 'workflow_blueprint_review', 'pending', {sql_literal(priority)}, {tag()});"
        )

    for review_type, priority in [
        ("payload_schema_review", "high"),
        ("privacy_review", "high"),
        ("consent_review", "high"),
        ("error_handling_review", "high"),
        ("activation_review", "urgent"),
    ]:
        sql.append(
            "INSERT INTO launch_n8n_review_items (launch_project_id, workflow_blueprint_id, payload_schema_id, review_type, status, priority, raw_context) "
            f"VALUES ({sql_literal(project_id)}, {sql_literal(lead_intake_id)}, {sql_literal(schema_id)}, "
            f"{sql_literal(review_type)}, 'pending', {sql_literal(priority)}, {tag()});"
        )

    for tid in test_ids:
        sql.append(
            "INSERT INTO launch_n8n_review_items (launch_project_id, workflow_blueprint_id, test_case_id, review_type, status, priority, raw_context) "
            f"VALUES ({sql_literal(project_id)}, {sql_literal(lead_intake_id)}, {sql_literal(tid)}, "
            f"'test_case_review', 'pending', 'normal', {tag()});"
        )

    sql.append("COMMIT;")
    code, out = run_psql("\n".join(sql))
    if code != 0:
        print(f"DB write FAILED (rolled back): {out[:400]}")
        return 2
    print("APPLIED: Phase 7.4 n8n workflow blueprints seeded. No n8n workflows, webhooks, inbound leads, contacts, sends, publishing, or external API calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
