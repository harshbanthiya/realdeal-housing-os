#!/usr/bin/env python3
"""Phase 7.24 - review DLF Wix AI implementation route.

Dry-run by default. Reviews ignored Phase 7.23 generated artifacts and records the least-manual
AI-assisted implementation route. This script does not call Wix APIs, request/read/store Wix API
keys, install Wix CLI, connect GitHub, publish, create live forms/webhooks/tracking, or touch
inbound leads/contacts/messages. It never prints the staging URL or artifact contents.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, sql_literal

import argparse
import json
import re
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.24"
SOURCE = "dlf_wix_ai_implementation_route_review"
ALLOWED_ROUTES = ("auto", "wix_git_cli", "wix_custom_element_velo", "wix_code_snippet")
EXPECTED_ARTIFACTS = {
    "implementation_readme": "implementation-readme.md",
    "wix_permission_route_analysis": "wix-permission-route-analysis.md",
    "wix_git_cli_setup_checklist": "wix-git-cli-setup-checklist.md",
    "gallery_white_custom_element": "gallery-white-custom-element.js",
    "gallery_white_custom_element_css": "gallery-white-custom-element.css",
    "gallery_white_page_code": "gallery-white-page-code.js",
    "gallery_white_copy_blocks": "gallery-white-copy-blocks.md",
    "gallery_white_form_config": "gallery-white-form-config.md",
    "gallery_white_seo_meta": "gallery-white-seo-meta.md",
    "gallery_white_static_preview": "gallery-white-static-preview.html",
    "gallery_white_static_preview_css": "gallery-white-static-preview.css",
}
def json_literal(value) -> str:
    return sql_literal(json.dumps(value, sort_keys=True))
def probe_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
plan_pick AS (
  SELECT e.*
  FROM wix_ai_build_execution_plans e
  WHERE e.launch_project_id IN (SELECT id FROM proj)
  ORDER BY e.created_at DESC
  LIMIT 1
)
SELECT
  (SELECT count(*) FROM proj),
  (SELECT count(*) FROM plan_pick),
  (SELECT count(*) FROM wix_ai_implementation_route_decisions rd WHERE rd.launch_project_id IN (SELECT id FROM proj) AND rd.raw_context->>'phase' = '{PHASE}' AND rd.raw_context->>'source' = '{SOURCE}'),
  (SELECT count(*) FROM wix_ai_build_artifacts a WHERE a.execution_plan_id IN (SELECT id FROM plan_pick)),
  (SELECT count(*) FROM wix_ai_build_validation_results v WHERE v.execution_plan_id IN (SELECT id FROM plan_pick) AND v.validation_status = 'failed'),
  (SELECT count(*) FROM wix_staging_sites s WHERE s.launch_project_id IN (SELECT id FROM proj) AND (s.real_domain_connected OR s.public_indexing_enabled OR s.page_published OR s.live_form_created OR s.live_webhook_created OR s.external_tracking_enabled OR s.wix_api_call_made)),
  (SELECT count(*) FROM wix_api_key_profiles WHERE profile_status IN ('active', 'created_externally') OR secret_value_stored OR external_call_allowed),
  (SELECT count(*) FROM inbound_leads),
  (SELECT count(*) FROM contacts),
  (SELECT send_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT publish_enabled_count FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT communication_sent FROM vw_dlf_operator_safety_posture WHERE launch_key = {lk}),
  (SELECT ready_for_fake_lead_test::text FROM vw_dlf_wix_staging_build_progress WHERE launch_key = {lk}),
  (SELECT ready_for_production_publish::text FROM vw_dlf_wix_staging_readiness WHERE launch_key = {lk});
"""

def metadata_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
WITH proj AS (SELECT id FROM launch_projects WHERE launch_key = {lk}),
plan_pick AS (
  SELECT e.*
  FROM wix_ai_build_execution_plans e
  WHERE e.launch_project_id IN (SELECT id FROM proj)
  ORDER BY e.created_at DESC
  LIMIT 1
)
SELECT 'plan', id::text, launch_project_id::text, preferred_route, fallback_route, execution_status, ''
FROM plan_pick
UNION ALL
SELECT 'artifact', a.id::text, a.launch_project_id::text, a.artifact_key, a.artifact_type, a.artifact_status, a.artifact_path
FROM wix_ai_build_artifacts a
WHERE a.execution_plan_id IN (SELECT id FROM plan_pick)
ORDER BY 1, 4, 5;
"""

def scan_artifact(path: Path, artifact_type: str) -> dict:
    exists = path.exists()
    text = path.read_text(errors="ignore") if exists else ""
    secret_assignment = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[\"'][^\"'\[\]<]{8,}[\"']")
    webhook = re.compile(r"(?i)https?://[^\s\"']*webhook[^\s\"']*")
    email = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
    phone = re.compile(r"(?<![\w-])\+?\d[\d\s().-]{8,}\d(?![\w-])")
    staging_url = re.compile(r"(?i)https?://[^\s\"']*(wixstudio\.com|wixsite\.com)[^\s\"']*")
    placeholder = re.compile(r"\b(RERA_VERIFY|PRICE_VERIFY|BROCHURE_LINK_PENDING|WIX_PAGE_PENDING|VERIFY|VISUAL_DIRECTION_PENDING)\b|\bpreview only\b|do not submit real data yet", re.I)
    seo_dom = re.compile(r"<h1|<h2|<title|meta name=\"description\"", re.I)
    no_secret = not secret_assignment.search(text)
    no_key = not secret_assignment.search(text)
    no_webhook = not webhook.search(text)
    no_private = not email.search(text) and not phone.search(text) and not staging_url.search(text)
    placeholders_ok = bool(placeholder.search(text)) if artifact_type in {
        "custom_element_js", "form_config", "copy_blocks"
    } else True
    seo_in_dom = bool(seo_dom.search(text)) if artifact_type == "static_preview_html" else False
    suitable = exists and no_secret and no_key and no_webhook and no_private and placeholders_ok
    status = "passed" if suitable else "needs_more_info"
    return {
        "exists": exists,
        "lines": text.count("\n") + (1 if text else 0),
        "bytes": path.stat().st_size if exists else 0,
        "no_secret": no_secret,
        "no_key": no_key,
        "no_webhook": no_webhook,
        "placeholders": placeholders_ok,
        "seo_dom": seo_in_dom,
        "suitable": suitable,
        "status": status,
        "secret_hits": len(secret_assignment.findall(text)),
        "webhook_hits": len(webhook.findall(text)),
        "email_hits": len(email.findall(text)),
        "phone_hits": len(phone.findall(text)),
        "staging_url_hits": len(staging_url.findall(text)),
    }

def route_payload(selected_route: str, artifact_count: int) -> tuple[str, str, str, list[dict], list[dict]]:
    route = "wix_git_cli" if selected_route == "auto" else selected_route
    if route == "wix_git_cli":
        fallback = "wix_custom_element_velo"
        status = "pending"
        operator_tasks = [
            ("check_git_integration_available", "check_git_integration_available", "Confirm whether Wix Git Integration + Wix CLI for Sites is available for the blank staging site.", "Do not publish, connect domain, enable indexing, or create live forms."),
            ("connect_github_repo", "connect_github_repo", "If available, connect the Wix staging site to a GitHub repository controlled by the operator.", "Do not paste secrets or Wix API keys into GitHub, chat, or the repo."),
            ("install_wix_cli", "install_wix_cli", "Install/use Wix CLI for Sites only when explicitly approved by the operator.", "Do not install during this review phase."),
            ("preview_site", "preview_site", "Preview the staging site after AI-assisted sync/paste is complete.", "Preview only; no production publish."),
            ("report_status", "report_status", "Report whether Git/CLI setup succeeded or whether fallback route is needed.", "Report status only; do not expose the staging URL."),
            ("fallback_enable_velo_if_git_unavailable", "enable_velo", "If Git/CLI is unavailable, enable Velo/dev mode for the Custom Element fallback.", "Fallback only; do not create live integrations."),
            ("fallback_add_custom_element_if_git_unavailable", "add_custom_element", "If Git/CLI is unavailable, add one Custom Element container for the generated component.", "Minimum setup only, not manual section-by-section build."),
        ]
        execution_steps = [
            ("sync_generated_code", "sync_code", "codex", "Sync or prepare generated Gallery White code through the Wix Git/CLI route after operator setup."),
            ("verify_local_preview", "verify_preview", "codex", "Verify the local/staging preview with DOM SEO text, placeholders, and no live submission path."),
            ("report_build_status", "report_wix_build_status", "codex", "Report build status and remaining blocked gates without printing the staging URL."),
        ]
    elif route == "wix_custom_element_velo":
        fallback = "wix_code_snippet"
        status = "pending"
        operator_tasks = [
            ("enable_velo", "enable_velo", "Enable Velo/dev mode for the staging site.", "No live backend integrations."),
            ("add_custom_element", "add_custom_element", "Add one Custom Element container to host the generated Gallery White component.", "Minimum platform setup only."),
            ("preview_site", "preview_site", "Preview the staging page after code paste/sync.", "Preview only; no production publish."),
            ("report_status", "report_status", "Report whether the Custom Element renders correctly.", "Do not expose the staging URL."),
        ]
        execution_steps = [
            ("prepare_custom_element_code", "generate_final_custom_element", "codex", "Prepare final Custom Element JS/CSS from generated artifacts."),
            ("paste_or_sync_custom_element_code", "paste_code", "codex", "Paste or sync Custom Element code after operator setup."),
            ("paste_or_sync_page_code", "paste_code", "codex", "Paste or sync Velo page code with no live webhook/API key."),
            ("verify_preview", "verify_preview", "codex", "Verify the staging preview layout and safety flags."),
            ("report_build_status", "report_wix_build_status", "codex", "Report build status and blockers."),
        ]
    else:
        fallback = "blocked"
        status = "pending"
        operator_tasks = [
            ("open_wix_custom_code_or_embed", "paste_custom_element_code", "Open the safest Wix-supported custom-code/embed surface.", "Last resort only; not preferred."),
            ("preview_site", "preview_site", "Preview the embedded snippet route.", "Preview only; no production publish."),
            ("report_status", "report_status", "Report whether snippet fallback is viable.", "Do not expose the staging URL."),
        ]
        execution_steps = [
            ("prepare_snippet", "generate_final_custom_element", "codex", "Prepare snippet fallback from the generated artifact package."),
            ("paste_snippet", "paste_code", "codex", "Paste snippet only after operator confirms no better route exists."),
            ("verify_preview", "verify_preview", "codex", "Verify rendered preview."),
            ("report_build_status", "report_wix_build_status", "codex", "Report status and blockers."),
        ]
    return route, fallback, status, [
        {"key": k, "type": t, "instruction": i, "safety": s} for k, t, i, s in operator_tasks
    ], [
        {"key": k, "type": t, "owner": o, "instruction": i} for k, t, o, i in execution_steps
    ]

def insert_sql(args, metadata: dict, artifact_reviews: list[dict], operator_tasks: list[dict], execution_steps: list[dict], route: str, fallback: str, status: str) -> str:
    route_id = str(uuid.uuid4())
    lp = metadata["launch_project_id"]
    plan_id = metadata["plan_id"]
    all_artifacts_passed = all(item["review_status"] == "passed" for item in artifact_reviews)
    route_status = "approved_for_operator_setup" if args.approve_safe_route and all_artifacts_passed else status
    review_status = "approved" if args.approve_safe_route and all_artifacts_passed else "pending"
    route_context = {
        "phase": PHASE,
        "source": SOURCE,
        "reviewed_by": args.reviewed_by,
        "selected_route_arg": args.selected_route,
        "fallback_route": fallback,
        "artifact_reviews": len(artifact_reviews),
    }
    statements = [
        "BEGIN;",
        f"""
INSERT INTO wix_ai_implementation_route_decisions (
  id, launch_project_id, execution_plan_id, selected_route, route_decision_status,
  reason_summary, operator_setup_required, ai_execution_possible, code_artifacts_ready,
  requires_wix_api_key, requires_publish_permission, requires_live_webhook, requires_tracking,
  requires_domain_connection, manual_drag_drop_required, safe_summary, raw_context
) VALUES (
  {sql_literal(route_id)}, {sql_literal(lp)}, {sql_literal(plan_id)}, {sql_literal(route)}, {sql_literal(route_status)},
  {sql_literal(args.decision_notes)}, true, true, {sql_literal(all_artifacts_passed)},
  false, false, false, false, false, false,
  {sql_literal('AI-assisted route review complete; no manual drag/drop build required.')},
  {json_literal(route_context)}
);
""",
    ]
    artifact_review_ids: list[str] = []
    for item in artifact_reviews:
        review_id = str(uuid.uuid4())
        artifact_review_ids.append(review_id)
        statements.append(f"""
INSERT INTO wix_ai_artifact_review_results (
  id, route_decision_id, execution_plan_id, artifact_id, artifact_key, artifact_type,
  file_present, review_status, no_secret_detected, no_api_key_detected, no_webhook_detected,
  placeholders_preserved, seo_text_in_dom, suitable_for_ai_execution, safe_summary, raw_context
) VALUES (
  {sql_literal(review_id)}, {sql_literal(route_id)}, {sql_literal(plan_id)}, {sql_literal(item.get('artifact_id'))},
  {sql_literal(item['artifact_key'])}, {sql_literal(item['artifact_type'])}, {sql_literal(item['file_present'])},
  {sql_literal(item['review_status'])}, {sql_literal(item['no_secret_detected'])},
  {sql_literal(item['no_api_key_detected'])}, {sql_literal(item['no_webhook_detected'])},
  {sql_literal(item['placeholders_preserved'])}, {sql_literal(item['seo_text_in_dom'])},
  {sql_literal(item['suitable_for_ai_execution'])}, {sql_literal(item['safe_summary'])},
  {json_literal(item['raw_context'])}
);
""")
    operator_task_ids: list[str] = []
    for order, task in enumerate(operator_tasks, 1):
        task_id = str(uuid.uuid4())
        operator_task_ids.append(task_id)
        statements.append(f"""
INSERT INTO wix_ai_operator_setup_tasks (
  id, route_decision_id, launch_project_id, task_key, task_order, task_status,
  task_owner, task_type, instruction, safety_note, minimum_manual_action, raw_context
) VALUES (
  {sql_literal(task_id)}, {sql_literal(route_id)}, {sql_literal(lp)}, {sql_literal(task['key'])}, {order},
  'pending', 'operator', {sql_literal(task['type'])}, {sql_literal(task['instruction'])},
  {sql_literal(task['safety'])}, true, {json_literal({'phase': PHASE, 'source': SOURCE, 'fallback_route': fallback})}
);
""")
    execution_step_ids: list[str] = []
    for order, step in enumerate(execution_steps, 1):
        step_id = str(uuid.uuid4())
        execution_step_ids.append(step_id)
        statements.append(f"""
INSERT INTO wix_ai_execution_package_steps (
  id, route_decision_id, launch_project_id, step_key, step_order, step_status,
  agent_owner, step_type, safe_summary, agent_instruction, raw_context
) VALUES (
  {sql_literal(step_id)}, {sql_literal(route_id)}, {sql_literal(lp)}, {sql_literal(step['key'])}, {order},
  'planned', {sql_literal(step['owner'])}, {sql_literal(step['type'])},
  {sql_literal('AI-executable staging implementation step; blocked until operator setup/review clears.')},
  {sql_literal(step['instruction'])}, {json_literal({'phase': PHASE, 'source': SOURCE, 'selected_route': route})}
);
""")
    review_items = [
        ("route_decision_review", "high", None, None, None),
        ("artifact_review", "high", artifact_review_ids[0] if artifact_review_ids else None, None, None),
        ("operator_setup_review", "normal", None, operator_task_ids[0] if operator_task_ids else None, None),
        ("ai_execution_review", "normal", None, None, execution_step_ids[0] if execution_step_ids else None),
        ("custom_element_review", "normal", None, None, None),
        ("velo_review", "normal", None, None, None),
        ("safety_review", "high", None, None, None),
        ("publish_blocker_review", "high", None, None, None),
    ]
    for review_type, priority, artifact_review_id, operator_task_id, execution_step_id in review_items:
        status_value = "pending" if review_type == "publish_blocker_review" else review_status
        statements.append(f"""
INSERT INTO wix_ai_implementation_review_items (
  launch_project_id, route_decision_id, artifact_review_id, operator_task_id, execution_step_id,
  review_type, status, priority, reviewed_by, reviewed_at, decision_notes, raw_context
) VALUES (
  {sql_literal(lp)}, {sql_literal(route_id)}, {sql_literal(artifact_review_id)}, {sql_literal(operator_task_id)},
  {sql_literal(execution_step_id)}, {sql_literal(review_type)}, {sql_literal(status_value)}, {sql_literal(priority)},
  {sql_literal(args.reviewed_by if status_value == 'approved' else None)},
  {'now()' if status_value == 'approved' else 'NULL'}, {sql_literal(args.decision_notes if status_value == 'approved' else None)},
  {json_literal({'phase': PHASE, 'source': SOURCE, 'publish_blocker_kept_pending': review_type == 'publish_blocker_review'})}
);
""")
    statements.append("COMMIT;")
    statements.append(counts_sql(args.launch_key))
    return "\n".join(statements)

def counts_sql(launch_key: str) -> str:
    lk = sql_literal(launch_key)
    return f"""
SELECT 'route_decisions', selected_route, route_decision_status, count(*)::text
FROM wix_ai_implementation_route_decisions rd
JOIN launch_projects p ON p.id = rd.launch_project_id
WHERE p.launch_key = {lk} AND rd.raw_context->>'phase' = '{PHASE}'
GROUP BY selected_route, route_decision_status
UNION ALL
SELECT 'artifact_reviews', artifact_type, review_status, count(*)::text
FROM wix_ai_artifact_review_results ar
JOIN wix_ai_implementation_route_decisions rd ON rd.id = ar.route_decision_id
JOIN launch_projects p ON p.id = rd.launch_project_id
WHERE p.launch_key = {lk} AND rd.raw_context->>'phase' = '{PHASE}'
GROUP BY artifact_type, review_status
UNION ALL
SELECT 'operator_tasks', task_type, task_status, count(*)::text
FROM wix_ai_operator_setup_tasks t
JOIN wix_ai_implementation_route_decisions rd ON rd.id = t.route_decision_id
JOIN launch_projects p ON p.id = t.launch_project_id
WHERE p.launch_key = {lk} AND rd.raw_context->>'phase' = '{PHASE}'
GROUP BY task_type, task_status
UNION ALL
SELECT 'execution_steps', step_type, step_status, count(*)::text
FROM wix_ai_execution_package_steps s
JOIN wix_ai_implementation_route_decisions rd ON rd.id = s.route_decision_id
JOIN launch_projects p ON p.id = s.launch_project_id
WHERE p.launch_key = {lk} AND rd.raw_context->>'phase' = '{PHASE}'
GROUP BY step_type, step_status
UNION ALL
SELECT 'implementation_reviews', review_type, status, count(*)::text
FROM wix_ai_implementation_review_items ri
JOIN wix_ai_implementation_route_decisions rd ON rd.id = ri.route_decision_id
JOIN launch_projects p ON p.id = ri.launch_project_id
WHERE p.launch_key = {lk} AND rd.raw_context->>'phase' = '{PHASE}'
GROUP BY review_type, status
ORDER BY 1, 2, 3;
"""

def main() -> int:
    parser = argparse.ArgumentParser(description="Review DLF Wix AI implementation route. Dry-run by default.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--selected-route", choices=ALLOWED_ROUTES, default="auto")
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--decision-notes", required=True)
    parser.add_argument("--approve-safe-route", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    print(f"DLF Wix AI implementation route review. launch_key={args.launch_key}. Counts only.")
    if not args.real_ok:
        print("Refusing: --real-ok is required, even for dry-run.")
        return 1

    code, probe = run_psql(probe_sql(args.launch_key))
    if code != 0:
        print(probe)
        return code
    fields = probe.split("|")
    if len(fields) < 14:
        print("Refusing: baseline probe returned no usable result.")
        return 1
    project_count, plan_count, existing, artifacts, failures, live_flags, active_keys, inbound, contacts, send, publish, sent = (int(x or 0) for x in fields[:12])
    fake_ready, prod_ready = fields[12:14]
    if project_count != 1 or plan_count != 1:
        print("Refusing: launch project or Phase 7.23 execution plan is missing.")
        return 1
    if existing:
        print("Refusing: Phase 7.24 route-review rows already exist. Cleanup first if this is intentional.")
        return 1
    if artifacts < len(EXPECTED_ARTIFACTS) or failures or live_flags or active_keys or inbound or contacts != 4 or send or publish or sent or fake_ready == "true" or prod_ready == "true":
        print("Refusing: baseline safety counts are not clean.")
        return 1

    code, meta = run_psql(metadata_sql(args.launch_key))
    if code != 0:
        print(meta)
        return code
    metadata: dict[str, str] = {}
    artifacts_meta: list[dict] = []
    for row in meta.splitlines():
        parts = row.split("|")
        if parts[0] == "plan":
            metadata = {"plan_id": parts[1], "launch_project_id": parts[2], "preferred_route": parts[3], "fallback_route": parts[4]}
        elif parts[0] == "artifact":
            artifacts_meta.append({
                "artifact_id": parts[1],
                "launch_project_id": parts[2],
                "artifact_key": parts[3],
                "artifact_type": parts[4],
                "artifact_status": parts[5],
                "artifact_path": parts[6],
            })
    if not metadata or not artifacts_meta:
        print("Refusing: missing Phase 7.23 artifact metadata.")
        return 1

    route, fallback, status, operator_tasks, execution_steps = route_payload(args.selected_route, len(artifacts_meta))
    artifact_reviews: list[dict] = []
    for art in artifacts_meta:
        path = PROJECT_ROOT / art["artifact_path"]
        scan = scan_artifact(path, art["artifact_type"])
        artifact_reviews.append({
            "artifact_id": art["artifact_id"],
            "artifact_key": art["artifact_key"],
            "artifact_type": art["artifact_type"],
            "file_present": scan["exists"],
            "review_status": scan["status"],
            "no_secret_detected": scan["no_secret"],
            "no_api_key_detected": scan["no_key"],
            "no_webhook_detected": scan["no_webhook"],
            "placeholders_preserved": scan["placeholders"],
            "seo_text_in_dom": scan["seo_dom"],
            "suitable_for_ai_execution": scan["suitable"],
            "safe_summary": "Artifact present and clean for AI-assisted implementation." if scan["status"] == "passed" else "Artifact missing or needs more information.",
            "raw_context": {
                "phase": PHASE,
                "source": SOURCE,
                "line_count": scan["lines"],
                "byte_count": scan["bytes"],
                "secret_hits": scan["secret_hits"],
                "webhook_hits": scan["webhook_hits"],
                "email_hits": scan["email_hits"],
                "phone_hits": scan["phone_hits"],
                "staging_url_hits": scan["staging_url_hits"],
            },
        })

    print("projected route-review rows:")
    print(f"  route decisions: 1   selected_route: {route}   fallback_route: {fallback}")
    print(f"  artifact reviews: {len(artifact_reviews)}   passed: {sum(1 for a in artifact_reviews if a['review_status'] == 'passed')}   needs_more_info: {sum(1 for a in artifact_reviews if a['review_status'] != 'passed')}")
    print(f"  operator setup tasks: {len(operator_tasks)}   pending: {len(operator_tasks)}")
    print(f"  AI execution steps: {len(execution_steps)}   planned: {len(execution_steps)}")
    print(f"  implementation review items: 8   approved_now: {7 if args.approve_safe_route else 0}   publish_blocker_review_pending: 1")
    print("  requires_wix_api_key / publish_permission / live_webhook / tracking / domain / manual_drag_drop: 0")
    print("  Wix API calls / key reads / publish / leads / contacts / messages: 0")

    if not args.apply:
        print("Dry run only. No database rows were written.")
        print("Writing requires BOTH --real-ok and --apply.")
        return 0

    sql = insert_sql(args, metadata, artifact_reviews, operator_tasks, execution_steps, route, fallback, status)
    code, output = run_psql(sql)
    if code != 0:
        print(output)
        return code
    print(output)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
