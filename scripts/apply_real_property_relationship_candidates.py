#!/usr/bin/env python3
"""Phase 5.8 — first REAL owner/unit relationship CANDIDATE apply. Dry-run by default.

For one canonical contact (created by an applied canonical merge), materialise a
single review-gated candidate chain from its source-aware owner/unit signals:
  canonical contact -> building -> building_alias (pending_review)
  -> building_unit (needs_review) -> contact_property_relationship (pending_review)
  -> property_relationship_review_item (pending).

Nothing is approved or activated: the relationship stays 'pending_review' and the
review item stays 'pending'. Writing requires BOTH --real-ok and --apply. All rows
are tagged phase=5.8 + the rel-label so the companion rollback can remove them.
Counts only; building/unit identifiers (property data) may be shown; never prints
person names, phones, emails, websites, or addresses. No communications are sent.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
DEFAULT_REL_LABEL = "REAL_PHASE_5_8_OWNER_UNIT_RELATIONSHIP_001"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def sql_literal(value: str | None) -> str:
    if value is None:
        return "NULL"
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


def tag(rel_label: str, extra: str = "") -> str:
    base = (
        "jsonb_build_object('phase','5.8','rel_label'," + sql_literal(rel_label)
        + ",'source','real_property_relationship_candidate'"
    )
    return base + (extra + ")" if extra else ")")


def probe_sql(contact_id: str, rel_label: str) -> str:
    cid = sql_literal(contact_id)
    return f"""
WITH ctx AS (
  SELECT c.id AS contact_id,
    (c.is_test = false) AS non_test,
    (c.canonical_status = 'active') AS active,
    (SELECT cml.contact_import_row_id
       FROM canonical_merge_links cml
       JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
       WHERE cml.canonical_contact_id = c.id AND cml.merge_action = 'create_contact' AND cmb.status = 'applied'
       ORDER BY cmb.applied_at DESC NULLS LAST, cmb.created_at DESC LIMIT 1) AS cir_id
  FROM contacts c WHERE c.id = {cid}
),
sig AS (
  SELECT ctx.contact_id, ctx.non_test, ctx.active, ctx.cir_id,
    COALESCE((SELECT NULLIF(btrim(building_name),'') FROM contact_property_hints WHERE contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1),
             (SELECT NULLIF(btrim(building_name),'') FROM inventory_import_rows WHERE owner_contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1)) AS building_name,
    COALESCE((SELECT NULLIF(btrim(building_code),'') FROM contact_property_hints WHERE contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1),
             (SELECT NULLIF(btrim(building_code),'') FROM inventory_import_rows WHERE owner_contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1)) AS building_code,
    COALESCE((SELECT NULLIF(btrim(unit_number),'') FROM contact_property_hints WHERE contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1),
             (SELECT NULLIF(btrim(unit_number),'') FROM inventory_import_rows WHERE owner_contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1)) AS unit_number
  FROM ctx
)
SELECT
  (SELECT count(*) FROM ctx WHERE contact_id IS NOT NULL),
  COALESCE((SELECT non_test FROM ctx), false),
  COALESCE((SELECT active FROM ctx), false),
  (SELECT count(*) FROM ctx WHERE cir_id IS NOT NULL),
  COALESCE((SELECT (building_name IS NOT NULL OR building_code IS NOT NULL) FROM sig), false),
  COALESCE((SELECT (unit_number IS NOT NULL) FROM sig), false),
  EXISTS (SELECT 1 FROM contact_property_relationships WHERE contact_id = {cid} AND raw_context->>'phase' = '5.8'),
  EXISTS (SELECT 1 FROM contact_property_relationships WHERE raw_context->>'rel_label' = {sql_literal(rel_label)}),
  COALESCE((SELECT building_name FROM sig), ''),
  COALESCE((SELECT unit_number FROM sig), '');
"""


def apply_sql(contact_id: str, rel_label: str, review_item_id: str | None) -> str:
    cid = sql_literal(contact_id)
    rl = sql_literal(rel_label)
    rl_tag = tag(rel_label)
    rel_tag = tag(rel_label, ",'review_item_id'," + sql_literal(review_item_id)) if review_item_id else rl_tag
    return f"""
BEGIN;
CREATE TEMP TABLE tmp_sig AS
WITH ctx AS (
  SELECT c.id AS contact_id,
    (SELECT cml.contact_import_row_id
       FROM canonical_merge_links cml
       JOIN canonical_merge_batches cmb ON cmb.id = cml.merge_batch_id
       WHERE cml.canonical_contact_id = c.id AND cml.merge_action = 'create_contact' AND cmb.status = 'applied'
       ORDER BY cmb.applied_at DESC NULLS LAST, cmb.created_at DESC LIMIT 1) AS cir_id
  FROM contacts c WHERE c.id = {cid} AND c.is_test = false AND c.canonical_status = 'active'
)
SELECT ctx.contact_id, ctx.cir_id, cir.import_batch_id, cir.source_format,
  (SELECT id FROM contact_property_hints WHERE contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1) AS hint_id,
  (SELECT id FROM inventory_import_rows WHERE owner_contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1) AS inv_id,
  COALESCE((SELECT NULLIF(btrim(building_name),'') FROM contact_property_hints WHERE contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1),
           (SELECT NULLIF(btrim(building_name),'') FROM inventory_import_rows WHERE owner_contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1)) AS building_name,
  COALESCE((SELECT NULLIF(btrim(building_code),'') FROM contact_property_hints WHERE contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1),
           (SELECT NULLIF(btrim(building_code),'') FROM inventory_import_rows WHERE owner_contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1)) AS building_code,
  COALESCE((SELECT NULLIF(btrim(wing),'') FROM contact_property_hints WHERE contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1),
           (SELECT NULLIF(btrim(wing),'') FROM inventory_import_rows WHERE owner_contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1)) AS wing,
  COALESCE((SELECT NULLIF(btrim(unit_number),'') FROM contact_property_hints WHERE contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1),
           (SELECT NULLIF(btrim(unit_number),'') FROM inventory_import_rows WHERE owner_contact_import_row_id = ctx.cir_id ORDER BY created_at LIMIT 1)) AS unit_number,
  CASE WHEN EXISTS (SELECT 1 FROM inventory_import_rows WHERE owner_contact_import_row_id = ctx.cir_id) THEN 'owner' ELSE 'owner' END AS rel_type,
  (SELECT sf.id FROM source_files sf WHERE sf.import_batch_id = cir.import_batch_id ORDER BY sf.created_at LIMIT 1) AS source_file_id
FROM ctx JOIN contact_import_rows cir ON cir.id = ctx.cir_id;

DO $$
BEGIN
  IF (SELECT count(*) FROM tmp_sig) <> 1 THEN
    RAISE EXCEPTION 'Expected exactly 1 candidate signal row, got %.', (SELECT count(*) FROM tmp_sig);
  END IF;
  IF (SELECT building_name IS NULL AND building_code IS NULL FROM tmp_sig) THEN
    RAISE EXCEPTION 'Refusing: no building signal for this contact.';
  END IF;
  IF (SELECT unit_number IS NULL FROM tmp_sig) THEN
    RAISE EXCEPTION 'Refusing: no unit signal (owner/unit relationship needs a unit).';
  END IF;
END $$;

WITH nb AS (
  INSERT INTO buildings (name, city, notes, metadata)
  SELECT COALESCE(s.building_name, s.building_code), 'Mumbai',
         'Building anchor created by Phase 5.8 owner/unit relationship candidate (review-gated).',
         {rl_tag}
  FROM tmp_sig s RETURNING id
),
na AS (
  INSERT INTO building_aliases (building_id, alias_text, alias_type, normalized_alias, source_file_id, source_format, confidence, status, notes, metadata)
  SELECT nb.id, COALESCE(s.building_code, s.building_name), 'import_alias',
         lower(COALESCE(s.building_code, s.building_name)), s.source_file_id, s.source_format, 0.700,
         'pending_review', 'Phase 5.8 building alias candidate.', {rl_tag}
  FROM nb, tmp_sig s RETURNING id
),
nu AS (
  INSERT INTO building_units (building_id, building_name, building_code, wing, unit_number, canonical_status, source_file_id, source_import_row_id, confidence, metadata)
  SELECT nb.id, s.building_name, s.building_code, s.wing, s.unit_number, 'needs_review',
         s.source_file_id, s.cir_id, 0.700, {rl_tag}
  FROM nb, tmp_sig s RETURNING id
),
nr AS (
  INSERT INTO contact_property_relationships (contact_id, building_id, building_unit_id, source_contact_import_row_id, source_property_hint_id, source_inventory_import_row_id, source_file_id, relationship_type, relationship_status, confidence, notes, raw_context)
  SELECT s.contact_id, nb.id, nu.id, s.cir_id, s.hint_id, s.inv_id, s.source_file_id, s.rel_type,
         'pending_review', 0.700,
         'Phase 5.8 first real owner/unit relationship candidate (review-gated).', {rel_tag}
  FROM nb, nu, tmp_sig s RETURNING id
)
INSERT INTO property_relationship_review_items (contact_property_relationship_id, contact_id, building_id, building_unit_id, review_type, status, priority, title, summary, recommended_action, raw_context)
SELECT nr.id, s.contact_id, nb.id, nu.id, 'owner_tenant_review', 'pending', 'normal',
       'Phase 5.8 owner/unit relationship candidate',
       'First real owner/unit relationship candidate for review (building + unit + owner).',
       'review_relationship', {rl_tag}
FROM nr, nb, nu, tmp_sig s;
COMMIT;

SELECT 'buildings' AS item, count(*)::text AS val FROM buildings WHERE metadata->>'rel_label' = {rl}
UNION ALL SELECT 'building_aliases', count(*)::text FROM building_aliases WHERE metadata->>'rel_label' = {rl}
UNION ALL SELECT 'building_units', count(*)::text FROM building_units WHERE metadata->>'rel_label' = {rl}
UNION ALL SELECT 'contact_property_relationships', count(*)::text FROM contact_property_relationships WHERE raw_context->>'rel_label' = {rl}
UNION ALL SELECT 'property_relationship_review_items', count(*)::text FROM property_relationship_review_items WHERE raw_context->>'rel_label' = {rl}
ORDER BY item;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply ONE real Phase 5.8 owner/unit relationship candidate. Dry-run by default.")
    parser.add_argument("--contact-id", required=True)
    parser.add_argument("--rel-label", default=DEFAULT_REL_LABEL)
    parser.add_argument("--review-item-id")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--real-ok", action="store_true")
    args = parser.parse_args()

    if args.rel_label.startswith("FAKE_"):
        print("Refusing: --rel-label must not start with FAKE_ (this is the real candidate path).")
        return 1

    print(f"Phase 5.8 real relationship candidate apply. contact={args.contact_id}; rel_label={args.rel_label}. Counts only.")

    code, probe = run_psql(probe_sql(args.contact_id, args.rel_label))
    if code != 0:
        print(probe)
        return code
    f = probe.split("|")
    if len(f) < 10:
        print("Refusing: probe returned no usable result.")
        return 1
    contact_found = int(f[0] or 0)
    non_test = f[1].strip() == "t"
    active = f[2].strip() == "t"
    has_row = int(f[3] or 0)
    has_building = f[4].strip() == "t"
    has_unit = f[5].strip() == "t"
    existing_phase58 = f[6].strip() == "t"
    rel_label_used = f[7].strip() == "t"
    building_name = f[8]
    unit_number = f[9]

    if contact_found != 1:
        print("Refusing: canonical contact not found.")
        return 1
    if not non_test:
        print("Refusing: contact is is_test=true (this path is for real canonical contacts only).")
        return 1
    if not active:
        print("Refusing: contact canonical_status is not 'active'.")
        return 1
    if has_row != 1:
        print("Refusing: contact has no applied create_contact merge link (no source import row).")
        return 1
    if not has_building:
        print("Refusing: no building signal for this contact's source row.")
        return 1
    if not has_unit:
        print("Refusing: no unit signal (owner/unit relationship needs a unit).")
        return 1
    if existing_phase58 or rel_label_used:
        print("Refusing: a Phase 5.8 relationship candidate already exists for this contact/label. Use rollback first.")
        return 1

    print(f"signals: building={building_name!r} unit={unit_number!r} relationship_type=owner (all review-gated)")

    if not (args.apply and args.real_ok):
        print("Dry run only. No database writes were made.")
        print("planned (would create, all pending_review): buildings|1 building_aliases|1 building_units|1 relationships|1 review_items|1")
        print("Writing requires --apply and --real-ok.")
        return 0

    code, output = run_psql(apply_sql(args.contact_id, args.rel_label, args.review_item_id))
    print("Phase 5.8 candidate chain created (all review-gated):")
    print(output)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
