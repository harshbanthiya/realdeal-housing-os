#!/usr/bin/env python3
"""Phase 7.11 — create an inactive DLF n8n workflow template package.

Dry-run by default. The template is a local/importable artifact only: no n8n
API calls, no workflow creation, no activation, no live webhook, no credentials,
no inbound leads, no contacts, no sends, and no publishing.

Writing requires BOTH --real-ok and --apply. Counts only, plus artifact path.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.11"
SOURCE = "dlf_n8n_build_package"
PACKAGE_KEY = "dlf-westpark-lead-intake-inactive-template"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "exports" / "n8n_templates"
VALIDATIONS = (
    "no_credentials",
    "no_live_webhook_url",
    "no_activation",
    "placeholder_paths_only",
    "fake_payload_compatible",
    "no_send_nodes_enabled",
    "no_external_credentials",
)
REVIEWS = (
    ("build_package_review", "high"),
    ("security_review", "high"),
    ("privacy_review", "high"),
    ("manual_import_review", "normal"),
    ("activation_blocker_review", "blocker"),
)
def workflow_template() -> dict:
    nodes = [
        {
            "parameters": {
                "path": "webhook-test/dlf-westpark-lead-intake-placeholder",
                "httpMethod": "POST",
                "responseMode": "onReceived",
                "options": {"responseData": "firstEntryJson"},
            },
            "id": "01-placeholder-webhook",
            "name": "Placeholder Test Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [0, 0],
            "notes": "Inactive manual-import template. Placeholder test path only.",
        },
        {
            "parameters": {
                "conditions": {
                    "string": [
                        {"value1": "={{$json.launch_key}}", "operation": "isNotEmpty"},
                        {"value1": "={{$json.consent.status}}", "operation": "isNotEmpty"},
                    ]
                },
            },
            "id": "02-validate-payload",
            "name": "Validate Required Fields",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2,
            "position": [260, 0],
            "notes": "Validates structure only; no live lead write.",
        },
        {
            "parameters": {
                "mode": "manual",
                "assignments": {
                    "assignments": [
                        {"name": "launch_key", "value": "dlf-westpark-andheri-west", "type": "string"},
                        {"name": "source", "value": "placeholder_manual_test", "type": "string"},
                        {"name": "normalized_status", "value": "test_only", "type": "string"},
                    ]
                },
            },
            "id": "03-normalize-lead",
            "name": "Normalize Lead Payload",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3,
            "position": [520, 0],
            "notes": "Normalizes placeholder payload shape only.",
        },
        {
            "parameters": {
                "mode": "manual",
                "assignments": {
                    "assignments": [
                        {"name": "utm_source", "value": "={{$json.utm_source || 'placeholder'}}", "type": "string"},
                        {"name": "attribution_status", "value": "draft_rule_match_required", "type": "string"},
                    ]
                },
            },
            "id": "04-attribution",
            "name": "Map Attribution",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3,
            "position": [780, 0],
            "notes": "Maps UTM placeholders; no external calls.",
        },
        {
            "parameters": {
                "mode": "manual",
                "assignments": {
                    "assignments": [
                        {"name": "lead_score_band", "value": "review_required", "type": "string"},
                        {"name": "ready_for_live_capture", "value": False, "type": "boolean"},
                    ]
                },
            },
            "id": "05-score",
            "name": "Score Placeholder Lead",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3,
            "position": [1040, 0],
            "notes": "Scoring placeholder; live capture remains false.",
        },
        {
            "parameters": {
                "mode": "manual",
                "assignments": {
                    "assignments": [
                        {"name": "review_queue", "value": "launch_inbound_lead_review_items", "type": "string"},
                        {"name": "review_status", "value": "manual_review_required", "type": "string"},
                    ]
                },
            },
            "id": "06-review-task-placeholder",
            "name": "Create Review Task Placeholder",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3,
            "position": [1300, 0],
            "notes": "Placeholder only; does not insert into DB.",
        },
        {
            "parameters": {
                "mode": "manual",
                "assignments": {
                    "assignments": [
                        {"name": "whatsapp_send_enabled", "value": False, "type": "boolean"},
                        {"name": "email_send_enabled", "value": False, "type": "boolean"},
                    ]
                },
            },
            "id": "07-disabled-send-placeholders",
            "name": "Disabled Send Placeholders",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3,
            "position": [1560, 0],
            "disabled": True,
            "notes": "Disabled no-op placeholders. No messaging provider nodes.",
        },
    ]
    return {
        "name": "DLF Westpark Lead Intake - Inactive Manual Import Template",
        "active": False,
        "nodes": nodes,
        "connections": {
            "Placeholder Test Webhook": {
                "main": [[{"node": "Validate Required Fields", "type": "main", "index": 0}]]
            },
            "Validate Required Fields": {
                "main": [[{"node": "Normalize Lead Payload", "type": "main", "index": 0}], []]
            },
            "Normalize Lead Payload": {
                "main": [[{"node": "Map Attribution", "type": "main", "index": 0}]]
            },
            "Map Attribution": {
                "main": [[{"node": "Score Placeholder Lead", "type": "main", "index": 0}]]
            },
            "Score Placeholder Lead": {
                "main": [[{"node": "Create Review Task Placeholder", "type": "main", "index": 0}]]
            },
            "Create Review Task Placeholder": {
                "main": [[{"node": "Disabled Send Placeholders", "type": "main", "index": 0}]]
            },
        },
        "settings": {"executionOrder": "v1", "saveExecutionProgress": False},
        "staticData": None,
        "tags": ["manual-import-only", "inactive", "dlf-westpark", "phase-7-11"],
        "meta": {
            "phase": PHASE,
            "source": SOURCE,
            "manual_import_only": True,
            "workflow_created_in_n8n": False,
            "activation_requested": False,
            "live_capture_ready": False,
        },
    }

def artifact_paths(output_dir: str, allow_repo_template: bool) -> tuple[Path, Path | None]:
    out = Path(output_dir)
    if not out.is_absolute():
        out = PROJECT_ROOT / out
    artifact = out / f"{PACKAGE_KEY}.json"
    repo_copy = None
    if allow_repo_template:
        repo_copy = PROJECT_ROOT / "docs" / "examples" / f"{PACKAGE_KEY}.json"
    return artifact, repo_copy

def validate_template(template: dict) -> tuple[dict[str, str], str]:
    rendered = json.dumps(template, sort_keys=True)
    webhook_paths = [
        node.get("parameters", {}).get("path", "")
        for node in template.get("nodes", [])
        if node.get("type") == "n8n-nodes-base.webhook"
    ]
    send_nodes_enabled = [
        node for node in template.get("nodes", [])
        if "send" in node.get("name", "").lower() and not node.get("disabled", False)
    ]
    checks = {
        "no_credentials": "passed" if "\"credentials\"" not in rendered else "failed",
        "no_live_webhook_url": "passed" if "http://" not in rendered and "https://" not in rendered else "failed",
        "no_activation": "passed" if template.get("active") is False else "failed",
        "placeholder_paths_only": "passed" if webhook_paths == ["webhook-test/dlf-westpark-lead-intake-placeholder"] else "failed",
        "fake_payload_compatible": "passed" if template.get("meta", {}).get("live_capture_ready") is False else "failed",
        "no_send_nodes_enabled": "passed" if not send_nodes_enabled else "failed",
        "no_external_credentials": "passed" if "apiKey" not in rendered and "accessToken" not in rendered else "failed",
    }
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    return checks, digest

def apply_sql(launch_key: str, artifact_path: Path, digest: str, checks: dict[str, str]) -> str:
    lk = sql_literal(launch_key)
    rel_artifact = artifact_path.relative_to(PROJECT_ROOT) if artifact_path.is_relative_to(PROJECT_ROOT) else artifact_path
    validation_rows = []
    for vtype in VALIDATIONS:
        status = checks[vtype]
        validation_rows.append(
            f"({sql_literal(vtype)}, {sql_literal(status)}, "
            f"{sql_literal(vtype + ' -> ' + status)})"
        )
    review_rows = ", ".join(f"({sql_literal(rtype)}, {sql_literal(priority)})" for rtype, priority in REVIEWS)
    return f"""
BEGIN;

DO $GUARD$
DECLARE unsafe int; approved int;
BEGIN
  SELECT count(*) INTO unsafe
  FROM launch_n8n_build_packages bp
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk}
    AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}'
    AND (bp.workflow_created_in_n8n OR bp.activation_requested);
  SELECT count(*) INTO approved
  FROM launch_n8n_build_packages bp
  JOIN launch_projects p ON p.id = bp.launch_project_id
  WHERE p.launch_key = {lk}
    AND bp.raw_context->>'phase' = '{PHASE}'
    AND bp.raw_context->>'source' = '{SOURCE}'
    AND bp.package_status = 'approved_for_manual_import';
  IF unsafe > 0 THEN RAISE EXCEPTION 'Refusing: existing Phase 7.11 package is marked created/activation-requested.'; END IF;
  IF approved > 0 THEN RAISE EXCEPTION 'Refusing: existing Phase 7.11 package already approved for manual import.'; END IF;
END $GUARD$;

DELETE FROM launch_n8n_build_review_items ri
USING launch_n8n_build_packages bp, launch_projects p
WHERE ri.build_package_id = bp.id
  AND bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';

DELETE FROM launch_n8n_build_validation_results vr
USING launch_n8n_build_packages bp, launch_projects p
WHERE vr.build_package_id = bp.id
  AND bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';

DELETE FROM launch_n8n_build_packages bp
USING launch_projects p
WHERE bp.launch_project_id = p.id
  AND p.launch_key = {lk}
  AND bp.raw_context->>'phase' = '{PHASE}'
  AND bp.raw_context->>'source' = '{SOURCE}';

WITH project AS (
  SELECT id FROM launch_projects WHERE launch_key = {lk}
),
blueprint AS (
  SELECT wb.id
  FROM launch_n8n_workflow_blueprints wb
  JOIN project p ON p.id = wb.launch_project_id
  WHERE wb.workflow_type = 'lead_intake'
    AND wb.activation_status = 'not_created'
  ORDER BY wb.created_at
  LIMIT 1
),
pkg AS (
  INSERT INTO launch_n8n_build_packages
    (launch_project_id, workflow_blueprint_id, package_key, package_status, artifact_path,
     artifact_type, contains_credentials, contains_webhook_secret, contains_live_webhook_url,
     external_call_made, workflow_created_in_n8n, activation_requested, human_review_required,
     raw_context)
  SELECT p.id, b.id, {sql_literal(PACKAGE_KEY)}, 'validated', {sql_literal(str(rel_artifact))},
     'n8n_workflow_template_json', false, false, false, false, false, false, true,
     jsonb_build_object('phase','{PHASE}','source','{SOURCE}','artifact_sha256',{sql_literal(digest)})
  FROM project p
  JOIN blueprint b ON true
  RETURNING id, launch_project_id
),
validations AS (
  INSERT INTO launch_n8n_build_validation_results
    (build_package_id, validation_type, validation_status, safe_summary, raw_context)
  SELECT pkg.id, v.validation_type, v.validation_status, v.safe_summary,
    jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
  FROM pkg
  JOIN (VALUES {", ".join(validation_rows)}) AS v(validation_type, validation_status, safe_summary) ON true
  RETURNING id, build_package_id
)
INSERT INTO launch_n8n_build_review_items
  (launch_project_id, build_package_id, review_type, status, priority, raw_context)
SELECT pkg.launch_project_id, pkg.id, r.review_type, 'pending', r.priority,
  jsonb_build_object('phase','{PHASE}','source','{SOURCE}')
FROM pkg
JOIN (VALUES {review_rows}) AS r(review_type, priority) ON true;

DO $LIVE_GUARD$
DECLARE created int; activated int; inbound int; contacts_count int; send_count int; publish_count int;
BEGIN
  SELECT count(*) INTO created FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
    WHERE p.launch_key = {lk} AND bp.workflow_created_in_n8n;
  SELECT count(*) INTO activated FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id
    WHERE p.launch_key = {lk} AND bp.activation_requested;
  SELECT count(*) INTO inbound FROM inbound_leads;
  SELECT count(*) INTO contacts_count FROM contacts;
  SELECT send_enabled_count INTO send_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  SELECT publish_enabled_count INTO publish_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk};
  IF created > 0 OR activated > 0 THEN RAISE EXCEPTION 'Refusing: package flags indicate n8n creation/activation.'; END IF;
  IF inbound <> 0 THEN RAISE EXCEPTION 'Refusing: inbound lead count changed to %.', inbound; END IF;
  IF contacts_count <> 4 THEN RAISE EXCEPTION 'Refusing: contacts count changed to %.', contacts_count; END IF;
  IF send_count <> 0 OR publish_count <> 0 THEN RAISE EXCEPTION 'Refusing: send/publish enabled.'; END IF;
END $LIVE_GUARD$;

COMMIT;

SELECT 'build_packages', count(*)::text FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'validation_results', count(*)::text FROM launch_n8n_build_validation_results vr JOIN launch_n8n_build_packages bp ON bp.id = vr.build_package_id JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'review_items', count(*)::text FROM launch_n8n_build_review_items ri JOIN launch_n8n_build_packages bp ON bp.id = ri.build_package_id JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.raw_context->>'phase' = '{PHASE}'
UNION ALL SELECT 'workflow_created_in_n8n', count(*)::text FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.workflow_created_in_n8n
UNION ALL SELECT 'activation_requested', count(*)::text FROM launch_n8n_build_packages bp JOIN launch_projects p ON p.id = bp.launch_project_id WHERE p.launch_key = {lk} AND bp.activation_requested
UNION ALL SELECT 'ready_to_activate', ready_to_activate::text FROM vw_dlf_n8n_build_readiness WHERE launch_key = {lk}
ORDER BY 1;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Create inactive DLF n8n workflow template package. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR.relative_to(PROJECT_ROOT)))
    parser.add_argument("--allow-repo-template", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    artifact_path, repo_copy = artifact_paths(args.output_dir, args.allow_repo_template)
    template = workflow_template()
    checks, digest = validate_template(template)
    failures = sum(1 for status in checks.values() if status != "passed")

    print(f"DLF n8n inactive workflow package. launch_key={args.launch_key}. Counts only.")
    print(f"artifact_path={artifact_path}")
    print("projected:")
    print("  build packages: 1")
    print(f"  validation results: {len(VALIDATIONS)}")
    print(f"  review items: {len(REVIEWS)}")
    print(f"  validation_failures: {failures}")
    print("  n8n_api_calls: 0   workflows_created: 0   activation_requested: 0")
    print("  inbound_leads_created: 0   contacts_created_or_merged: 0   sends_or_publishing: 0")

    if failures:
        print("Refusing: local template validation failed before writing.")
        return 1

    if not (args.apply and args.real_ok):
        print("Dry run only. No artifact or database writes were made.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(template, indent=2, sort_keys=True) + "\n"
    artifact_path.write_text(rendered, encoding="utf-8")
    if repo_copy:
        repo_copy.parent.mkdir(parents=True, exist_ok=True)
        repo_copy.write_text(rendered, encoding="utf-8")
        print(f"repo_template_path={repo_copy}")

    code, output = run_psql(apply_sql(args.launch_key, artifact_path, digest, checks))
    print("Apply result:" if code == 0 else "Apply FAILED:")
    print(output)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
