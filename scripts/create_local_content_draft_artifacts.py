#!/usr/bin/env python3
"""Phase 6.4 local content draft workspace. Dry-run by default.

For one building web profile (default: imperial-heights-goregaon-west) it creates
INTERNAL, clearly-non-final draft artifacts from the existing content briefs:
an outline + internal_brief_notes per brief, plus a meta_tag_draft for the building
page; one draft review per artifact; and one source_gap_item per unresolved
(needed) source requirement that maps to a gap type.

It does NOT call any AI/external/Wix API, scrape the web, mark ai_agent_tasks
completed, produce final public content, set public_ready=true, or publish. Every
artifact keeps the safe defaults (internal_only=true, public_ready=false,
source_verification_required=true, human_review_required=true,
external_calls_made=false, published=false, communication_sent=false). Artifact
bodies contain only outlines/placeholders with [SOURCE NEEDED] markers and no
private contact data. Writing requires --real-ok AND --apply. Counts only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "6.4"
SOURCE = "local_content_draft_workspace"
HEADER = "INTERNAL DRAFT — NOT FOR PUBLISHING\nHuman review required."

# Briefs on the Imperial Heights profile: group -> (sql filter, title, target_keyword).
BRIEFS = {
    "building_page": ("cb.content_type = 'building_page'",
                      "Imperial Heights Goregaon West: Flats, Rent, Resale and Owner Listings",
                      "Imperial Heights Goregaon West"),
    "rent": ("cb.target_keyword = 'Imperial Heights flats for rent'",
             "Flats for Rent in Imperial Heights Goregaon West",
             "Imperial Heights flats for rent"),
    "resale": ("cb.target_keyword = 'Imperial Heights resale'",
               "Imperial Heights Goregaon West Resale Guide",
               "Imperial Heights resale"),
}

# requirement_type -> gap_type (unmapped types like building_facts/faq produce no gap).
REQUIREMENT_TO_GAP = {
    "rental_range": "rent_range_missing",
    "resale_range": "resale_range_missing",
    "amenities": "amenities_unverified",
    "developer_info": "developer_unverified",
    "location_landmarks": "landmarks_unverified",
    "internal_inventory": "inventory_availability_unverified",
    "legal_disclaimer": "legal_disclaimer_needed",
    "owner_relationships": "owner_listing_permission_needed",
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
    "'communication_sent', false, 'internal_only', true, 'is_real', true)"
)

PHASE_TABLES = [
    ("content_draft_artifacts", "raw_context"),
    ("content_draft_reviews", "raw_context"),
    ("content_source_gap_items", "raw_context"),
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


def outline_body(group: str, title: str, target: str) -> str:
    sections = {
        "building_page": [
            "Overview of Imperial Heights, Goregaon West [SOURCE NEEDED: building_facts]",
            "Location & nearby landmarks [SOURCE NEEDED: location_landmarks]",
            "Configurations & sizes [SOURCE NEEDED]",
            "Indicative rent range [SOURCE NEEDED: rental_range]",
            "Indicative resale range [SOURCE NEEDED: resale_range]",
            "Amenities [SOURCE NEEDED: amenities]",
            "Owner / listing section [SOURCE NEEDED: owner_listing_permission]",
            "FAQ [SOURCE NEEDED]",
            "Legal disclaimer [SOURCE NEEDED: legal_disclaimer]",
        ],
        "rent": [
            "Intro: renting in Imperial Heights, Goregaon West [SOURCE NEEDED]",
            "Indicative rent range by configuration [SOURCE NEEDED: rental_range]",
            "Available units (internal) [SOURCE NEEDED: internal_inventory]",
            "Nearby landmarks & connectivity [SOURCE NEEDED: location_landmarks]",
            "FAQ for renters [SOURCE NEEDED]",
            "Legal disclaimer [SOURCE NEEDED: legal_disclaimer]",
        ],
        "resale": [
            "Intro: buying resale in Imperial Heights [SOURCE NEEDED]",
            "Indicative resale price range [SOURCE NEEDED: resale_range]",
            "Available resale units (internal) [SOURCE NEEDED: internal_inventory]",
            "Developer / project background [SOURCE NEEDED: developer_info]",
            "FAQ for buyers [SOURCE NEEDED]",
            "Legal disclaimer [SOURCE NEEDED: legal_disclaimer]",
        ],
    }[group]
    lines = "\n".join(f"{i}. {s}" for i, s in enumerate(sections, 1))
    return (
        f"{HEADER}\n\n"
        f"Title: {title}\nTarget keyword: {target}\nType: {group}\n\n"
        f"Outline:\n{lines}\n\n"
        "TODO: collect & verify every [SOURCE NEEDED] item before any drafting.\n"
        "Do not invent facts. No availability promises. No contact/private data."
    )


def notes_body(group: str, title: str) -> str:
    return (
        f"{HEADER}\n\n"
        f"Internal brief notes for: {title}\n\n"
        "Status: outline only; sources NOT yet collected.\n"
        "All factual claims must be backed by a verified source before drafting; "
        "until then they stay marked [SOURCE NEEDED].\n"
        "No private contact data may appear in any draft.\n"
        "This artifact is internal_only and not public-ready."
    )


def meta_body(title: str, target: str) -> str:
    return (
        f"{HEADER}\n\n"
        "Meta tag DRAFT (placeholder, not final):\n"
        f"  metaTitle: \"{title}\" [REVIEW]\n"
        f"  metaDescription: \"[DRAFT] Imperial Heights, Goregaon West — flats, rent, "
        "resale and owner listings. [SOURCE NEEDED for any specific claim]\"\n"
        f"  h1: \"{target}\" [REVIEW]\n\n"
        "Do not publish. Human review required."
    )


def jsonb_lit(obj) -> str:
    return sql_literal(json.dumps(obj)) + "::jsonb"


def artifact_insert(profile: str, group: str, artifact_type: str, title: str,
                    target: str, body: str) -> str:
    filt = BRIEFS[group][0]
    summary = jsonb_lit({"group": group, "sources_state": "needed"})
    flags = jsonb_lit({"internal_draft": True, "source_needed": True, "not_final": True})
    return f"""
INSERT INTO content_draft_artifacts
  (content_brief_id, ai_agent_task_id, ai_task_execution_plan_id, artifact_type, artifact_status,
   title, target_keyword, artifact_body, source_requirements_summary, quality_flags, raw_context)
SELECT cb.id,
       (SELECT ep.ai_agent_task_id FROM ai_task_execution_plans ep WHERE ep.content_brief_id = cb.id ORDER BY ep.created_at LIMIT 1),
       (SELECT ep.id FROM ai_task_execution_plans ep WHERE ep.content_brief_id = cb.id ORDER BY ep.created_at LIMIT 1),
       {sql_literal(artifact_type)}, 'draft', {sql_literal(title)}, {sql_literal(target)},
       {sql_literal(body)}, {summary}, {flags}, {TAG}
FROM content_briefs cb
WHERE cb.building_web_profile_id = {profile} AND {filt};"""


def insert_sql(slug: str) -> str:
    profile = f"(SELECT id FROM building_web_profiles WHERE profile_slug = {sql_literal(slug)})"
    stmts = []

    # Artifacts: outline + internal_brief_notes per brief; meta_tag_draft for building page.
    for group, (_filt, title, target) in BRIEFS.items():
        stmts.append(artifact_insert(profile, group, "outline", title, target, outline_body(group, title, target)))
        stmts.append(artifact_insert(profile, group, "internal_brief_notes", title, target, notes_body(group, title)))
    stmts.append(artifact_insert(profile, "building_page", "meta_tag_draft",
                                 BRIEFS["building_page"][1], BRIEFS["building_page"][2],
                                 meta_body(BRIEFS["building_page"][1], BRIEFS["building_page"][2])))

    # One draft review per artifact created in this phase.
    stmts.append(f"""
INSERT INTO content_draft_reviews
  (content_draft_artifact_id, content_brief_id, review_type, status, priority, raw_context)
SELECT a.id, a.content_brief_id, 'internal_draft_review', 'pending', 'normal', {TAG}
FROM content_draft_artifacts a
WHERE a.raw_context->>'phase' = '{PHASE}' AND a.raw_context->>'source' = '{SOURCE}'
  AND a.content_brief_id IN (SELECT id FROM content_briefs WHERE building_web_profile_id = {profile});""")

    # Source gap items from unresolved (needed) source requirements that map to a gap type.
    map_values = ",\n      ".join(
        f"({sql_literal(rt)}, {sql_literal(gt)})" for rt, gt in REQUIREMENT_TO_GAP.items()
    )
    stmts.append(f"""
INSERT INTO content_source_gap_items
  (content_brief_id, content_draft_artifact_id, gap_type, status, priority, safe_summary, raw_context)
SELECT r.content_brief_id,
       (SELECT a.id FROM content_draft_artifacts a
         WHERE a.content_brief_id = r.content_brief_id AND a.artifact_type = 'internal_brief_notes'
           AND a.raw_context->>'phase' = '{PHASE}' LIMIT 1),
       m.gap_type, 'open', 'normal',
       'Unverified/needed source: ' || m.gap_type || ' (from requirement ' || r.requirement_type || ').',
       {TAG}
FROM content_source_requirements r
JOIN (VALUES
    {map_values}
) AS m(requirement_type, gap_type) ON m.requirement_type = r.requirement_type
WHERE r.status = 'needed'
  AND r.content_brief_id IN (SELECT id FROM content_briefs WHERE building_web_profile_id = {profile});""")

    body = "\n".join(stmts)
    return f"BEGIN;\n{body}\nCOMMIT;\n{counts_sql()}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create local internal content draft artifacts. Dry-run by default.")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    print(f"Local content draft workspace. phase={PHASE}; source={SOURCE}; profile_slug={args.profile_slug}. "
          "Counts only; internal-only artifacts; no AI/external calls; nothing published or sent.")

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
        print("content_draft_artifacts planned: 7 (3 outlines + 3 internal_brief_notes + 1 meta_tag_draft; all internal_only, public_ready=false)")
        print("content_draft_reviews planned: 7 (status='pending')")
        print("content_source_gap_items planned: 17 (status='open'; from needed source requirements)")
        print("external_calls_made=false  published=false  communication_sent=false  public_ready=false")
        print("current phase-6.4 rows:")
        print(current)
        print("Writing requires --real-ok and --apply.")
        return 0

    if already:
        print("Refusing: phase-6.4 rows already exist. Run cleanup_local_content_draft_artifacts.py first.")
        print(current)
        return 1

    code, output = run_psql(insert_sql(args.profile_slug))
    print("Local content draft workspace rows created (counts):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
