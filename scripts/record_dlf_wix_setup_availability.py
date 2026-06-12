#!/usr/bin/env python3
"""Phase 7.25 - record DLF Wix setup availability.

Dry-run by default. Records operator-reported availability of Wix Git Integration, Wix CLI,
Velo, Custom Element, and code-paste paths. This script does not call Wix APIs, request/read/store
Wix API keys, install Wix CLI, connect GitHub, publish, create live forms/webhooks/tracking, or
touch inbound leads/contacts/messages. It never prints the staging URL.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "7.25"
SOURCE = "dlf_wix_setup_availability"


CAPABILITY_ARGS = {
    "git_integration": ("wix_git_integration", "git_integration_available", "git_integration_unavailable"),
    "wix_cli": ("wix_cli_for_sites", "wix_cli_available", "wix_cli_unavailable"),
    "github_connection": ("github_connection", "github_connection_available", "github_connection_unavailable"),
    "velo": ("velo_dev_mode", "velo_available", "velo_unavailable"),
    "custom_element": ("custom_element", "custom_element_available", "custom_element_unavailable"),
    "code_paste": ("code_paste", "code_paste_available", "code_paste_unavailable"),
}


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


def json_literal(value) -> str:
    return sql_literal(json.dumps(value, sort_keys=True))


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


def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
decision AS (
  SELECT rd.*
  FROM wix_ai_implementation_route_decisions rd
  WHERE rd.launch_project_id IN (SELECT id FROM proj)
  ORDER BY rd.created_at DESC
  LIMIT 1
)
SELECT
  (SELECT count(*) FROM proj),
  (SELECT count(*) FROM decision),
  (SELECT count(*) FROM wix_ai_selected_execution_paths sp WHERE sp.launch_project_id IN (SELECT id FROM proj) AND sp.raw_context->>'phase' = '{PHASE}' AND sp.raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM wix_staging_sites s WHERE s.launch_project_id IN (SELECT id FROM proj) AND (s.real_domain_connected OR s.public_indexing_enabled OR s.page_published OR s.live_form_created OR s.live_webhook_created OR s.external_tracking_enabled OR s.wix_api_call_made)),
  (SELECT count(*) FROM wix_api_key_profiles WHERE profile_status IN ('active', 'created_externally') OR secret_value_stored OR external_call_allowed),
  (SELECT count(*) FROM inbound_leads),
  (SELECT count(*) FROM contacts),
  (SELECT send_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT publish_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT communication_sent FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT ready_for_fake_lead_test::text FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk}),
  (SELECT ready_for_production_publish::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk}),
  (SELECT id::text FROM decision),
  (SELECT launch_project_id::text FROM decision);
"""


def status_from_args(args, key: str) -> str:
    _, available_attr, unavailable_attr = CAPABILITY_ARGS[key]
    if getattr(args, available_attr):
        return "available"
    if getattr(args, unavailable_attr):
        return "unavailable"
    if args.mark_needs_more_info:
        return "needs_more_info"
    return "pending"


def selected_path(args) -> tuple[str, str, str]:
    selections = [args.select_git_cli, args.select_custom_element, args.select_code_snippet, args.mark_needs_more_info]
    if sum(1 for item in selections if item) != 1:
        raise ValueError("Select exactly one of --select-git-cli, --select-custom-element, --select-code-snippet, or --mark-needs-more-info.")
    if args.select_git_cli:
        if not (args.git_integration_available and args.wix_cli_available):
            return "wix_git_cli", "needs_more_info", "Git/CLI selected but Git Integration and Wix CLI availability still need confirmation."
        return "wix_git_cli", "needs_operator_setup", "Operator confirmed Git Integration and Wix CLI path are available for staging setup."
    if args.select_custom_element:
        if not (args.velo_available and args.custom_element_available):
            return "wix_custom_element_velo", "needs_more_info", "Custom Element path selected but Velo and Custom Element availability still need confirmation."
        return "wix_custom_element_velo", "needs_operator_setup", "Operator confirmed Velo and Custom Element fallback are available for staging setup."
    if args.select_code_snippet:
        if not args.code_paste_available:
            return "wix_code_snippet", "needs_more_info", "Snippet path selected but code-paste availability still needs confirmation."
        return "wix_code_snippet", "needs_operator_setup", "Operator confirmed code-paste fallback is available for staging setup."
    return "blocked", "needs_more_info", "Operator has not yet confirmed Wix Git Integration, Wix CLI, Velo, or Custom Element availability."


def validate_args(args) -> tuple[bool, str]:
    if not args.real_ok:
        return False, "Refusing: --real-ok is required, even for dry-run."
    required = (
        args.confirm_no_wix_api_key,
        args.confirm_no_wix_api_call,
        args.confirm_real_domain_not_connected,
        args.confirm_public_indexing_disabled,
        args.confirm_page_not_published,
        args.confirm_no_live_form,
        args.confirm_no_live_webhook,
        args.confirm_no_external_tracking,
    )
    if not all(required):
        return False, "Refusing: all safety confirmation flags are required."
    for key, (_, available_attr, unavailable_attr) in CAPABILITY_ARGS.items():
        if getattr(args, available_attr) and getattr(args, unavailable_attr):
            return False, f"Refusing: {key} cannot be both available and unavailable."
    try:
        selected_path(args)
    except ValueError as exc:
        return False, str(exc)
    return True, ""


def counts_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT 'availability_checks', capability_type, check_status, count(*)::text
FROM wix_ai_setup_availability_checks c
JOIN launch_projects p ON p.id = c.launch_project_id
WHERE p.launch_key = {lk} AND c.raw_context->>'phase' = '{PHASE}'
GROUP BY capability_type, check_status
UNION ALL
SELECT 'selected_paths', selected_path, path_status, count(*)::text
FROM wix_ai_selected_execution_paths sp
JOIN launch_projects p ON p.id = sp.launch_project_id
WHERE p.launch_key = {lk} AND sp.raw_context->>'phase' = '{PHASE}'
GROUP BY selected_path, path_status
UNION ALL
SELECT 'setup_reviews', review_type, status, count(*)::text
FROM wix_ai_setup_review_items ri
JOIN launch_projects p ON p.id = ri.launch_project_id
WHERE p.launch_key = {lk} AND ri.raw_context->>'phase' = '{PHASE}'
GROUP BY review_type, status
ORDER BY 1, 2, 3;
"""


def insert_sql(args, launch_project_id: str, route_decision_id: str, path: str, path_status: str, reason: str) -> str:
    selected_path_id = str(uuid.uuid4())
    context = {
        "phase": PHASE,
        "source": SOURCE,
        "reported_by": args.reported_by,
        "decision_notes": args.decision_notes,
        "confirmations": {
            "no_wix_api_key": args.confirm_no_wix_api_key,
            "no_wix_api_call": args.confirm_no_wix_api_call,
            "real_domain_not_connected": args.confirm_real_domain_not_connected,
            "public_indexing_disabled": args.confirm_public_indexing_disabled,
            "page_not_published": args.confirm_page_not_published,
            "no_live_form": args.confirm_no_live_form,
            "no_live_webhook": args.confirm_no_live_webhook,
            "no_external_tracking": args.confirm_no_external_tracking,
        },
    }
    statements = ["BEGIN;"]
    availability_ids: dict[str, str] = {}
    for key, (capability_type, _, _) in CAPABILITY_ARGS.items():
        check_id = str(uuid.uuid4())
        availability_ids[capability_type] = check_id
        status = status_from_args(args, key)
        safe_summary = f"{capability_type} availability recorded as {status}; no API key, publish, or live webhook required."
        statements.append(f"""
INSERT INTO wix_ai_setup_availability_checks (
  id, launch_project_id, route_decision_id, check_key, check_status, capability_type,
  operator_reported, requires_api_key, requires_publish, requires_live_webhook, safe_summary, raw_context
) VALUES (
  {sql_literal(check_id)}, {sql_literal(launch_project_id)}, {sql_literal(route_decision_id)},
  {sql_literal(key)}, {sql_literal(status)}, {sql_literal(capability_type)}, true, false, false, false,
  {sql_literal(safe_summary)}, {json_literal(context)}
);
""")
    statements.append(f"""
INSERT INTO wix_ai_selected_execution_paths (
  id, launch_project_id, route_decision_id, selected_path, path_status, selection_reason,
  requires_operator_setup, requires_api_key, requires_publish, requires_live_webhook, requires_tracking,
  manual_drag_drop_required, safe_summary, raw_context
) VALUES (
  {sql_literal(selected_path_id)}, {sql_literal(launch_project_id)}, {sql_literal(route_decision_id)},
  {sql_literal(path)}, {sql_literal(path_status)}, {sql_literal(reason)}, true, false, false, false, false,
  false, {sql_literal('Wix setup path recorded without API key, publish, live webhook, tracking, or manual drag/drop requirement.')},
  {json_literal(context)}
);
""")
    reviews = [
        ("availability_review", "high", availability_ids.get("wix_git_integration"), None),
        ("selected_path_review", "high", None, selected_path_id),
        ("git_cli_review", "normal", availability_ids.get("wix_cli_for_sites"), selected_path_id if path == "wix_git_cli" else None),
        ("custom_element_review", "normal", availability_ids.get("custom_element"), selected_path_id if path == "wix_custom_element_velo" else None),
        ("safety_review", "high", None, selected_path_id),
    ]
    for review_type, priority, check_id, path_id in reviews:
        statements.append(f"""
INSERT INTO wix_ai_setup_review_items (
  launch_project_id, availability_check_id, selected_path_id, review_type, status, priority, raw_context
) VALUES (
  {sql_literal(launch_project_id)}, {sql_literal(check_id)}, {sql_literal(path_id)},
  {sql_literal(review_type)}, 'pending', {sql_literal(priority)}, {json_literal(context)}
);
""")
    if path == "wix_git_cli" and path_status == "needs_operator_setup":
        statements.append(f"""
UPDATE wix_ai_operator_setup_tasks
SET task_status = 'skipped',
    raw_context = raw_context || {json_literal({'phase_7_25_selection': 'wix_git_cli', 'skipped_reason': 'fallback task not needed while Git/CLI path is selected'})}::jsonb
WHERE route_decision_id = {sql_literal(route_decision_id)}
  AND task_type IN ('enable_velo', 'add_custom_element');
""")
    elif path == "wix_custom_element_velo" and path_status == "needs_operator_setup":
        statements.append(f"""
UPDATE wix_ai_operator_setup_tasks
SET task_status = 'skipped',
    raw_context = raw_context || {json_literal({'phase_7_25_selection': 'wix_custom_element_velo', 'skipped_reason': 'Git/CLI task not needed while Custom Element fallback is selected'})}::jsonb
WHERE route_decision_id = {sql_literal(route_decision_id)}
  AND task_type IN ('check_git_integration_available', 'connect_github_repo', 'install_wix_cli');
""")
    statements.append("COMMIT;")
    statements.append(counts_sql(args.launch_key))
    return "\n".join(statements)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record Phase 7.25 Wix setup availability. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--reported-by", required=True)
    parser.add_argument("--decision-notes", required=True)
    for key, (_, available_attr, unavailable_attr) in CAPABILITY_ARGS.items():
        parser.add_argument("--" + available_attr.replace("_", "-"), action="store_true")
        parser.add_argument("--" + unavailable_attr.replace("_", "-"), action="store_true")
    parser.add_argument("--select-git-cli", action="store_true")
    parser.add_argument("--select-custom-element", action="store_true")
    parser.add_argument("--select-code-snippet", action="store_true")
    parser.add_argument("--mark-needs-more-info", action="store_true")
    parser.add_argument("--confirm-no-wix-api-key", action="store_true")
    parser.add_argument("--confirm-no-wix-api-call", action="store_true")
    parser.add_argument("--confirm-real-domain-not-connected", action="store_true")
    parser.add_argument("--confirm-public-indexing-disabled", action="store_true")
    parser.add_argument("--confirm-page-not-published", action="store_true")
    parser.add_argument("--confirm-no-live-form", action="store_true")
    parser.add_argument("--confirm-no-live-webhook", action="store_true")
    parser.add_argument("--confirm-no-external-tracking", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Wix setup availability record. launch_key={args.launch_key}. Counts only.")
    ok, message = validate_args(args)
    if not ok:
        print(message)
        return 1
    path, path_status, reason = selected_path(args)

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 14:
        print("Refusing: baseline probe returned no usable result.")
        return 1
    project_count, decision_count, existing, live_flags, active_keys, inbound, contacts, send, publish, sent = (int(x or 0) for x in fields[:10])
    fake_ready, prod_ready, route_decision_id, launch_project_id = fields[10:14]
    if project_count != 1 or decision_count != 1:
        print("Refusing: launch project or Phase 7.24 route decision is missing.")
        return 1
    if existing:
        print("Refusing: Phase 7.25 setup availability rows already exist. Cleanup first if this is intentional.")
        return 1
    if live_flags or active_keys or inbound or contacts != 4 or send or publish or sent or fake_ready == "true" or prod_ready == "true":
        print("Refusing: safety counts are not clean.")
        return 1

    availability = {capability_type: status_from_args(args, key) for key, (capability_type, _, _) in CAPABILITY_ARGS.items()}
    print("projected setup availability rows:")
    for capability_type in sorted(availability):
        print(f"  {capability_type}: {availability[capability_type]}")
    print(f"  selected path: {path}   path_status: {path_status}")
    print("  setup review items: 5 pending")
    print("  requires_api_key / requires_publish / requires_live_webhook / requires_tracking / manual_drag_drop: 0")
    print("  Wix API calls / key reads / publish / leads / contacts / messages: 0")
    if not args.apply:
        print("Dry run only. No database rows were written.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    sql = insert_sql(args, launch_project_id, route_decision_id, path, path_status, reason)
    code, output = run_psql(sql)
    if code != 0:
        print(output)
        return code
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
