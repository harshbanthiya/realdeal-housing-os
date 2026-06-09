#!/usr/bin/env python3
"""Phase 6.2 guarded prep of Wix CMS mapping + content review + readiness rows.

Dry-run by default. For one building web profile (default: imperial-heights-goregaon-west)
it creates planning-only rows: two Wix CMS collections (building_pages, blog_posts),
draft field-mapping rows for the key fields, one pending content_review_item per
content brief, and a pending publishing_readiness_checks checklist per publishing-queue
row.

It does NOT publish, does NOT call Wix or any external API, does NOT approve any
review, does NOT mark anything ready to publish, and creates no content text beyond
the titles/metadata already present. Every row is tagged raw_context phase='6.2',
source='wix_content_review_prep', external_calls_made=false, published=false,
communication_sent=false. Writing requires --real-ok AND --apply. Counts only.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "6.2"
SOURCE = "wix_content_review_prep"

# Wix CMS collections to plan.
COLLECTIONS = [
    ("building_pages", "Building Pages", "Wix CMS collection for building SEO pages"),
    ("blog_posts", "Blog Posts", "Wix CMS collection for blog/guide content"),
]

# Field mappings: (collection_key, source_table, source_field, wix_field_key, wix_field_type, required).
MAPPINGS = [
    ("building_pages", "building_web_profiles", "building_name", "buildingName", "text", True),
    ("building_pages", "building_web_profiles", "profile_slug", "slug", "text", True),
    ("building_pages", "building_web_profiles", "area", "area", "text", False),
    ("building_pages", "building_web_profiles", "city", "city", "text", False),
    ("building_pages", "building_web_profiles", "developer", "developer", "text", False),
    ("building_pages", "building_web_profiles", "meta_title", "metaTitle", "text", True),
    ("building_pages", "building_web_profiles", "meta_description", "metaDescription", "text", False),
    ("building_pages", "building_web_profiles", "h1", "h1", "text", False),
    ("blog_posts", "content_briefs", "title", "contentTitle", "text", True),
    ("blog_posts", "content_briefs", "target_keyword", "targetKeyword", "text", False),
    ("blog_posts", "content_briefs", "content_type", "contentType", "text", False),
    ("blog_posts", "content_publishing_queue", "publish_status", "publishStatus", "text", False),
]

# Readiness checklist created per publishing-queue row (all start 'pending').
CHECK_TYPES = [
    "cms_mapping", "title_present", "slug_present", "meta_present",
    "human_approved", "no_external_call_required", "no_outreach", "wix_ready",
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
    ("wix_cms_collections", "raw_context"),
    ("wix_cms_field_mappings", "raw_context"),
    ("content_review_items", "raw_context"),
    ("publishing_readiness_checks", "raw_context"),
]


def counts_sql() -> str:
    parts = [
        f"SELECT '{t}' AS item, count(*)::text AS val FROM {t} "
        f"WHERE {col}->>'phase' = '{PHASE}' AND {col}->>'source' = '{SOURCE}'"
        for t, col in PHASE_TABLES
    ]
    return "\nUNION ALL ".join(parts) + "\nORDER BY item;"


def profile_id_sql(slug: str) -> str:
    return f"SELECT count(*) FROM building_web_profiles WHERE profile_slug = {sql_literal(slug)};"


def insert_sql(slug: str) -> str:
    s = sql_literal(slug)
    profile = f"(SELECT id FROM building_web_profiles WHERE profile_slug = {s})"

    coll_values = ",\n      ".join(
        f"({sql_literal(k)}, {sql_literal(n)}, {sql_literal(p)})"
        for (k, n, p) in COLLECTIONS
    )
    map_values = ",\n      ".join(
        f"({sql_literal(ck)}, {sql_literal(st)}, {sql_literal(sf)}, {sql_literal(wk)}, {sql_literal(wt)}, {str(req).lower()})"
        for (ck, st, sf, wk, wt, req) in MAPPINGS
    )
    check_values = ",\n      ".join(f"({sql_literal(c)})" for c in CHECK_TYPES)

    return f"""
BEGIN;
WITH coll AS (
  INSERT INTO wix_cms_collections (collection_key, collection_name, purpose, status, notes, raw_context)
  SELECT v.k, v.n, v.p, 'planned', 'Phase 6.2 planned Wix CMS collection.', {TAG}
  FROM (VALUES
      {coll_values}
  ) AS v(k, n, p)
  RETURNING id, collection_key
),
maps AS (
  INSERT INTO wix_cms_field_mappings
    (wix_cms_collection_id, source_table, source_field, wix_field_key, wix_field_type, required, status, notes, raw_context)
  SELECT coll.id, m.source_table, m.source_field, m.wix_field_key, m.wix_field_type, m.required,
         'draft', 'Phase 6.2 draft field mapping (review before use).', {TAG}
  FROM (VALUES
      {map_values}
  ) AS m(collection_key, source_table, source_field, wix_field_key, wix_field_type, required)
  JOIN coll ON coll.collection_key = m.collection_key
  RETURNING id
),
revs AS (
  INSERT INTO content_review_items
    (content_brief_id, building_web_profile_id, review_type, status, priority, raw_context)
  SELECT cb.id, cb.building_web_profile_id, 'brief_review', 'pending', 'normal', {TAG}
  FROM content_briefs cb
  WHERE cb.building_web_profile_id = {profile}
  RETURNING id
)
INSERT INTO publishing_readiness_checks
  (content_brief_id, content_publishing_queue_id, check_type, status, details, raw_context)
SELECT q.content_brief_id, q.id, ct.check_type, 'pending',
       'Phase 6.2 readiness check scaffold (awaiting human verification).', {TAG}
FROM content_publishing_queue q
JOIN content_briefs cb ON cb.id = q.content_brief_id
CROSS JOIN (VALUES
    {check_values}
) AS ct(check_type)
WHERE cb.building_web_profile_id = {profile};
COMMIT;
{counts_sql()}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Wix CMS mapping + content review rows. Dry-run by default.")
    parser.add_argument("--profile-slug", default="imperial-heights-goregaon-west")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    print(f"Wix content-review prep. phase={PHASE}; source={SOURCE}; profile_slug={args.profile_slug}. "
          "Counts only; no Wix/external calls; nothing published or sent.")

    if not args.real_ok:
        print("Refusing: --real-ok is required to operate on real planning data.")
        return 1

    code, found = run_psql(profile_id_sql(args.profile_slug))
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

    n_maps = len(MAPPINGS)
    n_checks = len(CHECK_TYPES)
    if not args.apply:
        print("Dry run only. No database writes were made.")
        print(f"wix_cms_collections planned: {len(COLLECTIONS)}")
        print(f"wix_cms_field_mappings planned: {n_maps} (status='draft')")
        print(f"content_review_items planned: 3 (status='pending', one per content brief)")
        print(f"publishing_readiness_checks planned: {n_checks} per publishing row x 3 rows = {n_checks * 3} (status='pending')")
        print("external_calls_made=false  published=false  communication_sent=false  ready_for_publish=false")
        print("current phase-6.2 rows:")
        print(current)
        print("Writing requires --real-ok and --apply.")
        return 0

    if already:
        print("Refusing: phase-6.2 rows already exist. Run cleanup_wix_content_review.py first.")
        print(current)
        return 1

    code, output = run_psql(insert_sql(args.profile_slug))
    print("Wix content-review prep rows created (counts):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
