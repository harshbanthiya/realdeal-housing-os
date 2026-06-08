#!/usr/bin/env python3
"""Phase 5.1 FAKE property-relationship workflow. Dry-run by default.

Creates one self-contained fake chain (building -> alias -> unit -> contact ->
relationship -> review item), every row tagged with fake_batch
'FAKE_PHASE_5_1_REL_001' and is_test markers so cleanup can remove them precisely.
Writing requires BOTH --apply and --fake-ok. Counts only; no raw personal values.
Never touches real canonical contacts or real buildings.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
FAKE_BATCH = "FAKE_PHASE_5_1_REL_001"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


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


FAKE_COUNTS_SQL = f"""
SELECT 'fake_buildings' AS item, count(*)::text AS val FROM buildings WHERE metadata->>'fake_batch' = '{FAKE_BATCH}'
UNION ALL SELECT 'fake_contacts', count(*)::text FROM contacts WHERE metadata->>'fake_batch' = '{FAKE_BATCH}'
UNION ALL SELECT 'fake_building_aliases', count(*)::text FROM building_aliases WHERE metadata->>'fake_batch' = '{FAKE_BATCH}'
UNION ALL SELECT 'fake_building_units', count(*)::text FROM building_units WHERE metadata->>'fake_batch' = '{FAKE_BATCH}'
UNION ALL SELECT 'fake_relationships', count(*)::text FROM contact_property_relationships WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}'
UNION ALL SELECT 'fake_review_items', count(*)::text FROM property_relationship_review_items WHERE raw_context->>'fake_batch' = '{FAKE_BATCH}'
ORDER BY item;
"""


def insert_sql() -> str:
    tag = (
        "jsonb_build_object('is_test', true, 'phase', '5.1', 'fake_batch', '"
        + FAKE_BATCH + "')"
    )
    return f"""
BEGIN;
WITH nb AS (
  INSERT INTO buildings (name, city, notes, metadata)
  VALUES ('FAKE Imperial Heights (Phase 5.1 test)', 'Mumbai',
          'Fake building created by Phase 5.1 relationship test.', {tag})
  RETURNING id
),
nc AS (
  INSERT INTO contacts (full_name, contact_type, source, status, tags, notes, metadata, is_test, canonical_status)
  VALUES ('FAKE Test Owner (Phase 5.1)', 'lead', '{FAKE_BATCH}', 'active',
          ARRAY['fake', 'phase_5_1', 'property_relationship']::text[],
          'Fake canonical contact created by Phase 5.1 relationship test.',
          {tag}, true, 'test')
  RETURNING id
),
na AS (
  INSERT INTO building_aliases (building_id, alias_text, alias_type, normalized_alias, status, notes, metadata)
  SELECT nb.id, 'IMP-HTS', 'google_maps_name', 'imp hts', 'pending_review',
         'Fake building alias (Phase 5.1).', {tag}
  FROM nb
  RETURNING id
),
nu AS (
  INSERT INTO building_units (building_id, building_name, building_code, wing, unit_number, typology, bhk, canonical_status, metadata)
  SELECT nb.id, 'FAKE Imperial Heights (Phase 5.1 test)', 'IMPH', 'A', '1001', 'apartment', '2BHK', 'active', {tag}
  FROM nb
  RETURNING id
),
nr AS (
  INSERT INTO contact_property_relationships (contact_id, building_id, building_unit_id, relationship_type, relationship_status, confidence, notes, raw_context)
  SELECT nc.id, nb.id, nu.id, 'owner', 'pending_review', 0.900,
         'Fake owner relationship (Phase 5.1).', {tag}
  FROM nc, nb, nu
  RETURNING id
)
INSERT INTO property_relationship_review_items (
  contact_property_relationship_id, contact_id, building_id, building_unit_id,
  review_type, status, priority, title, summary, recommended_action, raw_context
)
SELECT nr.id, nc.id, nb.id, nu.id, 'owner_tenant_review', 'pending', 'normal',
       'Fake owner review (Phase 5.1)',
       'Fake owner_tenant_review for the Phase 5.1 test relationship.',
       'approve_relationship', {tag}
FROM nr, nc, nb, nu;
COMMIT;
{FAKE_COUNTS_SQL}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create FAKE Phase 5.1 property relationships. Dry-run by default.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--fake-ok", action="store_true")
    args = parser.parse_args()

    print(f"Fake property relationship workflow. fake_batch={FAKE_BATCH}. Counts only.")

    code, existing = run_psql(FAKE_COUNTS_SQL)
    if code != 0:
        print(existing)
        return code
    already = any(int(line.split("|")[1]) > 0 for line in existing.splitlines() if "|" in line)

    if not (args.apply and args.fake_ok):
        print("Dry run only. No database writes were made.")
        print("planned (would create, all tagged fake/test):")
        print("  buildings|1\n  building_aliases|1\n  building_units|1\n  contacts|1\n  relationships|1\n  review_items|1")
        print("current fake rows present:")
        print(existing)
        print("Writing requires --apply and --fake-ok.")
        return 0

    if already:
        print("Refusing: fake rows for this batch already exist. Run cleanup_fake_property_relationships.py first.")
        print(existing)
        return 1

    code, output = run_psql(insert_sql())
    if code != 0:
        print(output)
        return code
    print("Fake rows created. Resulting fake counts:")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
