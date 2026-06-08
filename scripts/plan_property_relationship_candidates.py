#!/usr/bin/env python3
"""Plan building/unit/contact relationship candidates from source-aware data.

READ-ONLY: no database writes. Counts only; never prints names, phones, emails,
websites, or addresses. Planning sources (toggle with --include-* flags; if none
given, all are included): contact_property_hints + contact_import_rows parsed
fields (--include-property-hints), inventory_import_rows (--include-inventory-hints),
lead_requirements (--include-lead-requirements).

Classification rules:
  * building unknown but a building name/code is present -> building_alias candidate.
  * wing/unit present -> building_unit candidate.
  * no canonical contact -> skip 'needs_canonical_contact' (no relationship).
  * unit present + contact -> relationship candidate (unit-level, any type).
  * no unit, contact, building signal, and type in
    business_lead/interested_buyer/interested_tenant -> building-level relationship.
  * no unit + owner/tenant/etc -> skip 'owner_tenant_needs_unit'
    (owner/tenant relationships need unit or building confidence).
  * otherwise -> skip 'no_building_or_unit_signal'.
Nothing is auto-approved; every candidate is review-gated.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
BUILDING_LEVEL_TYPES = "('business_lead', 'interested_buyer', 'interested_tenant')"


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


PROPERTY_HINTS_SRC = """
SELECT 'property_hint' AS kind,
  COALESCE(cph.contact_id, cir.matched_contact_id, linked.canonical_contact_id) AS contact_id,
  cph.building_id AS building_id,
  (NULLIF(btrim(cph.building_name), '') IS NOT NULL OR NULLIF(btrim(cph.building_code), '') IS NOT NULL) AS has_bld,
  (NULLIF(btrim(cph.wing), '') IS NOT NULL OR NULLIF(btrim(cph.unit_number), '') IS NOT NULL) AS has_unit,
  COALESCE(NULLIF(btrim(cph.relationship_type), ''), 'unknown') AS rel_type,
  cir.source_format AS source_format,
  ib.source_name AS batch_label,
  COALESCE(c.is_test, false) AS is_test
FROM contact_property_hints cph
LEFT JOIN contact_import_rows cir ON cir.id = cph.contact_import_row_id
LEFT JOIN import_batches ib ON ib.id = cir.import_batch_id
LEFT JOIN LATERAL (
  SELECT cml.canonical_contact_id
  FROM canonical_merge_links cml
  JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
  WHERE cml.contact_import_row_id = cph.contact_import_row_id
    AND cml.merge_action = 'create_contact'
    AND cmb.status = 'applied'
  ORDER BY cmb.applied_at DESC NULLS LAST, cmb.created_at DESC
  LIMIT 1
) linked ON true
LEFT JOIN contacts c ON c.id = COALESCE(cph.contact_id, cir.matched_contact_id, linked.canonical_contact_id)
"""

IMPORT_ROW_SRC = """
SELECT 'import_row_parsed' AS kind,
  COALESCE(cir.matched_contact_id, linked.canonical_contact_id) AS contact_id,
  NULL::uuid AS building_id,
  (NULLIF(btrim(cir.parsed_building_name), '') IS NOT NULL OR NULLIF(btrim(cir.parsed_building_code), '') IS NOT NULL) AS has_bld,
  (NULLIF(btrim(cir.parsed_wing), '') IS NOT NULL OR NULLIF(btrim(cir.parsed_unit_number), '') IS NOT NULL) AS has_unit,
  'unknown' AS rel_type,
  cir.source_format AS source_format,
  ib.source_name AS batch_label,
  COALESCE(c.is_test, false) AS is_test
FROM contact_import_rows cir
LEFT JOIN import_batches ib ON ib.id = cir.import_batch_id
LEFT JOIN LATERAL (
  SELECT cml.canonical_contact_id
  FROM canonical_merge_links cml
  JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
  WHERE cml.contact_import_row_id = cir.id
    AND cml.merge_action = 'create_contact'
    AND cmb.status = 'applied'
  ORDER BY cmb.applied_at DESC NULLS LAST, cmb.created_at DESC
  LIMIT 1
) linked ON true
LEFT JOIN contacts c ON c.id = COALESCE(cir.matched_contact_id, linked.canonical_contact_id)
WHERE (
    NULLIF(btrim(cir.parsed_building_name), '') IS NOT NULL
    OR NULLIF(btrim(cir.parsed_building_code), '') IS NOT NULL
    OR NULLIF(btrim(cir.parsed_wing), '') IS NOT NULL
    OR NULLIF(btrim(cir.parsed_unit_number), '') IS NOT NULL
  )
  AND NOT EXISTS (
    SELECT 1
    FROM contact_property_hints cph
    WHERE cph.contact_import_row_id = cir.id
  )
"""

INVENTORY_SRC = """
SELECT 'inventory' AS kind,
  COALESCE(iir.owner_contact_id, iir.broker_contact_id, linked.canonical_contact_id) AS contact_id,
  iir.building_id AS building_id,
  (NULLIF(btrim(iir.building_name), '') IS NOT NULL OR NULLIF(btrim(iir.building_code), '') IS NOT NULL) AS has_bld,
  (NULLIF(btrim(iir.wing), '') IS NOT NULL OR NULLIF(btrim(iir.unit_number), '') IS NOT NULL) AS has_unit,
  CASE WHEN iir.broker_contact_id IS NOT NULL AND iir.owner_contact_id IS NULL THEN 'broker' ELSE 'owner' END AS rel_type,
  iir.source_format AS source_format,
  ib.source_name AS batch_label,
  COALESCE(c.is_test, false) AS is_test
FROM inventory_import_rows iir
LEFT JOIN import_batches ib ON ib.id = iir.import_batch_id
LEFT JOIN LATERAL (
  SELECT cml.canonical_contact_id
  FROM canonical_merge_links cml
  JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
  WHERE cml.contact_import_row_id = iir.owner_contact_import_row_id
    AND cml.merge_action = 'create_contact'
    AND cmb.status = 'applied'
  ORDER BY cmb.applied_at DESC NULLS LAST, cmb.created_at DESC
  LIMIT 1
) linked ON true
LEFT JOIN contacts c ON c.id = COALESCE(iir.owner_contact_id, iir.broker_contact_id, linked.canonical_contact_id)
"""

LEAD_REQ_SRC = """
SELECT 'lead_requirement' AS kind,
  COALESCE(lr.contact_id, linked.canonical_contact_id) AS contact_id,
  NULL::uuid AS building_id,
  false AS has_bld,
  false AS has_unit,
  CASE WHEN lr.purpose = 'buy' THEN 'interested_buyer'
       WHEN lr.purpose = 'rent' THEN 'interested_tenant'
       ELSE 'business_lead' END AS rel_type,
  lr.source_format AS source_format,
  ib.source_name AS batch_label,
  COALESCE(c.is_test, false) AS is_test
FROM lead_requirements lr
LEFT JOIN contact_import_rows cir ON cir.id = lr.contact_import_row_id
LEFT JOIN import_batches ib ON ib.id = cir.import_batch_id
LEFT JOIN LATERAL (
  SELECT cml.canonical_contact_id
  FROM canonical_merge_links cml
  JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
  WHERE cml.contact_import_row_id = lr.contact_import_row_id
    AND cml.merge_action = 'create_contact'
    AND cmb.status = 'applied'
  ORDER BY cmb.applied_at DESC NULLS LAST, cmb.created_at DESC
  LIMIT 1
) linked ON true
LEFT JOIN contacts c ON c.id = COALESCE(lr.contact_id, linked.canonical_contact_id)
"""


def plan_sql(sources: list[str], batch_label, source_format, fake_only, limit) -> str:
    union = "\nUNION ALL\n".join(f"({s})" for s in sources)
    conds = []
    if fake_only:
        conds.append("(batch_label LIKE 'FAKE_%' OR is_test = true)")
    if batch_label:
        conds.append(f"batch_label = {sql_literal(batch_label)}")
    if source_format:
        conds.append(f"source_format = {sql_literal(source_format)}")
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    limit_sql = f"LIMIT {int(limit)}" if limit else ""
    return f"""
WITH raw_src AS (
  {union}
),
src AS (
  SELECT * FROM raw_src
  {where}
  {limit_sql}
),
classified AS (
  SELECT
    (building_id IS NULL AND has_bld) AS needs_alias,
    has_unit AS needs_unit,
    CASE
      WHEN contact_id IS NULL THEN 'skip:needs_canonical_contact'
      WHEN has_unit THEN 'relationship:unit_level'
      WHEN (building_id IS NOT NULL OR has_bld)
           AND rel_type IN {BUILDING_LEVEL_TYPES} THEN 'relationship:building_level'
      WHEN rel_type IN ('owner', 'tenant', 'landlord', 'seller', 'buyer', 'broker', 'agent')
        THEN 'skip:owner_tenant_needs_unit'
      ELSE 'skip:no_building_or_unit_signal'
    END AS outcome
  FROM src
)
SELECT 'candidate_building_aliases' AS item, count(*) FILTER (WHERE needs_alias)::text AS val FROM classified
UNION ALL SELECT 'candidate_building_units', count(*) FILTER (WHERE needs_unit)::text FROM classified
UNION ALL SELECT 'candidate_contact_property_relationships', count(*) FILTER (WHERE outcome LIKE 'relationship:%')::text FROM classified
UNION ALL SELECT 'candidate_review_items', count(*) FILTER (WHERE outcome LIKE 'relationship:%')::text FROM classified
UNION ALL SELECT 'skipped_rows', count(*) FILTER (WHERE outcome LIKE 'skip:%')::text FROM classified
UNION ALL SELECT outcome, count(*)::text FROM classified WHERE outcome LIKE 'skip:%' GROUP BY outcome
UNION ALL SELECT 'rows_considered', count(*)::text FROM classified
ORDER BY item;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan property relationship candidates. Read-only; counts only.")
    parser.add_argument("--batch-label")
    parser.add_argument("--source-format")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--fake-only", action="store_true")
    parser.add_argument("--include-inventory-hints", action="store_true")
    parser.add_argument("--include-property-hints", action="store_true")
    parser.add_argument("--include-lead-requirements", action="store_true")
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        print("--limit must be positive.")
        return 1

    any_include = args.include_inventory_hints or args.include_property_hints or args.include_lead_requirements
    use_property = args.include_property_hints or not any_include
    use_inventory = args.include_inventory_hints or not any_include
    use_leads = args.include_lead_requirements or not any_include

    sources: list[str] = []
    if use_property:
        sources.append(PROPERTY_HINTS_SRC)
        sources.append(IMPORT_ROW_SRC)
    if use_inventory:
        sources.append(INVENTORY_SRC)
    if use_leads:
        sources.append(LEAD_REQ_SRC)

    print("Property relationship candidate plan. Read-only; counts only; no raw values printed.")
    print(f"sources: property_hints={use_property} inventory={use_inventory} lead_requirements={use_leads} fake_only={args.fake_only}")
    if args.batch_label:
        print(f"batch_label: {args.batch_label}")
    if args.source_format:
        print(f"source_format: {args.source_format}")

    code, output = run_psql(plan_sql(sources, args.batch_label, args.source_format, args.fake_only, args.limit))
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
