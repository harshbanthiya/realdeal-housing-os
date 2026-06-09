#!/usr/bin/env python3
"""Phase 6.3 guarded prep of content quality + AI execution planning. Dry-run by default.

For one building web profile (default: imperial-heights-goregaon-west) it creates
planning-only rows: a content_quality_checks checklist per content brief, the
content_source_requirements each brief needs before drafting, four reusable
ai_prompt_templates (created only if missing), and one ai_task_execution_plan per
existing queued ai_agent_task for the profile.

It does NOT execute any AI task, call Wix/any external API, scrape the web, generate
final article text, publish, send outreach, approve content reviews, or auto-pass any
check (all quality checks start 'pending', all source requirements start 'needed',
all execution plans default external_calls_allowed=false / requires_human_review=true).
Every row is tagged raw_context phase='6.3', source='content_quality_ai_planning',
external_calls_made=false, published=false, communication_sent=false. Writing requires
--real-ok AND --apply. Counts only; no raw personal values are printed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "6.3"
SOURCE = "content_quality_ai_planning"

# Quality checks created per brief: (check_key, severity). All start 'pending'.
QUALITY_CHECKS = [
    ("target_keyword_present", "normal"),
    ("search_intent_present", "normal"),
    ("outline_present", "normal"),
    ("source_requirements_present", "high"),
    ("local_market_claims_reviewed", "high"),
    ("no_unverified_claims", "blocker"),
    ("cms_mapping_exists", "normal"),
    ("human_review_required", "blocker"),
]

# Source requirements per brief group. All start 'needed'.
SOURCE_REQUIREMENTS = {
    "building_page": [
        "building_facts", "amenities", "location_landmarks", "rental_range",
        "resale_range", "internal_inventory", "owner_relationships", "legal_disclaimer",
    ],
    "rent": [
        "rental_range", "internal_inventory", "owner_relationships",
        "location_landmarks", "faq", "legal_disclaimer",
    ],
    "resale": [
        "resale_range", "internal_inventory", "owner_relationships",
        "developer_info", "faq", "legal_disclaimer",
    ],
}

# Common safety rules embedded in every prompt template.
SAFETY_RULES = [
    "cite_or_mark_source_needed",
    "do_not_invent_building_facts",
    "do_not_include_contact_or_private_data",
    "do_not_promise_availability",
    "no_outreach",
    "human_review_required",
]

# AI prompt templates (created if missing): (template_key, task_type, content_type, title, prompt_template, output_requirements).
PROMPT_TEMPLATES = [
    ("building_research_template", "building_research", "building_page",
     "Building research notes",
     "Research factual, citable information about {building_name} in {area}, {city}. "
     "For every fact include a [SOURCE NEEDED] placeholder. Do NOT invent amenities, "
     "prices, or availability. Do NOT include any contact or private data. Output "
     "research notes only; a human reviews before any use.",
     {"format": "research_notes", "must_include_source_placeholders": True}),
    ("keyword_research_template", "keyword_research", None,
     "Keyword research plan",
     "Propose additional low-competition keyword targets related to {building_name} "
     "({area}, {city}). Group by intent (rent/buy/research). Do not fabricate search "
     "volumes; mark estimates as [SOURCE NEEDED]. Output a keyword plan only.",
     {"format": "seo_update_plan", "group_by": "intent"}),
    ("blog_brief_template", "blog_brief", "blog",
     "Blog content brief",
     "Draft an OUTLINE (not a final article) for '{title}' targeting '{target_keyword}'. "
     "Mark every factual claim with [SOURCE NEEDED]. No availability promises, no "
     "contact data, no outreach. A human reviews the outline before drafting.",
     {"format": "content_outline", "final_article": False}),
    ("seo_monitoring_template", "seo_monitoring", None,
     "SEO monitoring plan",
     "Propose a plan to monitor search rankings for {building_name} keywords. "
     "Describe metrics and cadence only; do not call external APIs. Output a plan only.",
     {"format": "seo_update_plan", "external_calls": False}),
]

# ai_agent_task.task_type -> expected_output_type for execution plans.
OUTPUT_BY_TASK = {
    "building_research": "research_notes",
    "keyword_research": "seo_update_plan",
    "blog_brief": "content_outline",
    "seo_monitoring": "seo_update_plan",
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


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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


TAG = (
    "jsonb_build_object("
    f"'phase', '{PHASE}', 'source', '{SOURCE}', "
    "'external_calls_made', false, 'published', false, "
    "'communication_sent', false, 'is_real', true)"
)

PHASE_TABLES = [
    ("content_quality_checks", "raw_context"),
    ("content_source_requirements", "raw_context"),
    ("ai_prompt_templates", "raw_context"),
    ("ai_task_execution_plans", "raw_context"),
]


def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} "
        f"WHERE {col}->>'phase' = '{PHASE}' AND {col}->>'source' = '{SOURCE}'"
        for t, col in PHASE_TABLES
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"


def profile_exists_sql(slug: str) -> str:
    return f"SELECT count(*) FROM building_web_profiles WHERE profile_slug = {sql_literal(slug)};"


def jsonb_lit(obj) -> str:
    return sql_literal(json.dumps(obj)) + "::jsonb"


def insert_sql(slug: str) -> str:
    s = sql_literal(slug)
    profile = f"(SELECT id FROM building_web_profiles WHERE profile_slug = {s})"

    # 1. Quality checks (8 per brief on the profile).
    qc_values = ",\n      ".join(
        f"({sql_literal(k)}, {sql_literal(sev)})" for (k, sev) in QUALITY_CHECKS
    )
    quality_stmt = f"""
INSERT INTO content_quality_checks (content_brief_id, check_key, check_status, severity, details, raw_context)
SELECT cb.id, v.check_key, 'pending', v.severity,
       'Phase 6.3 quality check scaffold (awaiting human verification).', {TAG}
FROM content_briefs cb
CROSS JOIN (VALUES
    {qc_values}
) AS v(check_key, severity)
WHERE cb.building_web_profile_id = {profile};"""

    # 2. Source requirements per brief group.
    req_stmts = []
    group_filters = {
        "building_page": "cb.content_type = 'building_page'",
        "rent": "cb.target_keyword = 'Imperial Heights flats for rent'",
        "resale": "cb.target_keyword = 'Imperial Heights resale'",
    }
    for group, reqs in SOURCE_REQUIREMENTS.items():
        req_values = ",\n      ".join(f"({sql_literal(r)})" for r in reqs)
        req_stmts.append(f"""
INSERT INTO content_source_requirements (content_brief_id, requirement_type, status, source_notes, source_url_placeholder, raw_context)
SELECT cb.id, v.requirement_type, 'needed',
       'Phase 6.3 source requirement (collect/verify before drafting).', '[SOURCE URL NEEDED]', {TAG}
FROM content_briefs cb
CROSS JOIN (VALUES
    {req_values}
) AS v(requirement_type)
WHERE cb.building_web_profile_id = {profile} AND {group_filters[group]};""")

    # 3. Prompt templates (only those missing by template_key).
    tmpl_rows = ",\n      ".join(
        f"({sql_literal(k)}, {('NULL' if tt is None else sql_literal(tt))}, "
        f"{('NULL' if ct is None else sql_literal(ct))}, {sql_literal(title)}, "
        f"{sql_literal(prompt)}, {jsonb_lit(outreq)}, {jsonb_lit(SAFETY_RULES)})"
        for (k, tt, ct, title, prompt, outreq) in PROMPT_TEMPLATES
    )
    tmpl_stmt = f"""
INSERT INTO ai_prompt_templates
  (template_key, task_type, content_type, title, prompt_template, output_requirements, safety_rules, status, raw_context)
SELECT v.template_key, v.task_type, v.content_type, v.title, v.prompt_template,
       v.output_requirements, v.safety_rules, 'draft', {TAG}
FROM (VALUES
    {tmpl_rows}
) AS v(template_key, task_type, content_type, title, prompt_template, output_requirements, safety_rules)
WHERE NOT EXISTS (SELECT 1 FROM ai_prompt_templates e WHERE e.template_key = v.template_key);"""

    # 4. Execution plans: one per existing Phase-6.1 queued ai_agent_task for this profile.
    out_cases = " ".join(
        f"WHEN {sql_literal(tt)} THEN {sql_literal(ot)}" for tt, ot in OUTPUT_BY_TASK.items()
    )
    plan_stmt = f"""
INSERT INTO ai_task_execution_plans
  (ai_agent_task_id, content_brief_id, prompt_template_id, execution_status, execution_mode,
   external_calls_allowed, requires_human_review, planned_prompt_summary, expected_output_type, raw_context)
SELECT t.id,
       CASE WHEN t.entity_type = 'content_brief' THEN t.entity_id ELSE NULL END,
       (SELECT pt.id FROM ai_prompt_templates pt WHERE pt.task_type = t.task_type ORDER BY pt.created_at LIMIT 1),
       'planned', 'manual', false, true,
       'Planned manual, human-reviewed execution for ' || t.task_type || ' (no external calls).',
       CASE t.task_type {out_cases} ELSE 'research_notes' END,
       {TAG}
FROM ai_agent_tasks t
WHERE t.raw_input->>'phase' = '6.1'
  AND (
    (t.entity_type = 'content_brief' AND t.entity_id IN (SELECT id FROM content_briefs WHERE building_web_profile_id = {profile}))
    OR (t.entity_type = 'building' AND t.entity_id = (SELECT building_id FROM building_web_profiles WHERE id = {profile}))
  );"""

    body = "\n".join([quality_stmt] + req_stmts + [tmpl_stmt, plan_stmt])
    return f"BEGIN;\n{body}\nCOMMIT;\n{counts_sql()}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare content quality + AI execution plan rows. Dry-run by default.")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    print(f"Content quality / AI planning prep. phase={PHASE}; source={SOURCE}; profile_slug={args.profile_slug}. "
          "Counts only; no AI execution; no external calls; nothing published or sent.")

    if not args.real_ok:
        print("Refusing: --real-ok is required to operate on real planning data.")
        return 1

    code, found = run_psql(profile_exists_sql(args.profile_slug))
    if code != 0:
        print(found)
        return code
    if found.strip() != "1":
        print(f"Refusing: profile_slug {args.profile_slug} not found (matched {found}).")
        return 1

    code, current = run_psql(counts_sql())
    if code != 0:
        print(current)
        return code
    already = any(int(line.split("|")[1]) > 0 for line in current.splitlines() if "|" in line)

    if not args.apply:
        print("Dry run only. No database writes were made.")
        print(f"content_quality_checks planned: {len(QUALITY_CHECKS)} per brief x 3 = {len(QUALITY_CHECKS) * 3} (status='pending')")
        total_reqs = sum(len(v) for v in SOURCE_REQUIREMENTS.values())
        print(f"content_source_requirements planned: {total_reqs} (status='needed')")
        print(f"ai_prompt_templates planned: up to {len(PROMPT_TEMPLATES)} (only if missing; status='draft')")
        print("ai_task_execution_plans planned: one per Phase-6.1 queued AI task for the profile (expected 5)")
        print("external_calls_made=false  published=false  communication_sent=false  no checks auto-passed")
        print("current phase-6.3 rows:")
        print(current)
        print("Writing requires --real-ok and --apply.")
        return 0

    if already:
        print("Refusing: phase-6.3 rows already exist. Run cleanup_content_quality_plan.py first.")
        print(current)
        return 1

    code, output = run_psql(insert_sql(args.profile_slug))
    print("Content quality / AI planning rows created (counts):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
