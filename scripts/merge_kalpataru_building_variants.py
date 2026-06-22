"""Phase 6.23 — Merge Kalpataru Radiance duplicate building records into one canonical entry.

Problem: three buildings exist in the DB for the same physical complex:
  • "Kalpataru Radiance"              — canonical (717 units, 1627 reg records, 997 relationships)
  • "Kalpataru Radiance New Parser"   — duplicate from a second parsing pass (713 units, 102 records)
  • "Kalpataru Radiance A"            — Phase 6.18 test artifact (3 units, 3 SAMPLE records)

The canonical building is MISSING its RERA profile (P51800000591, verified) — it is trapped in
the duplicates. This script fixes that and consolidates all data.

What this does (in a single transaction):
  1. RERA profiles (2): both carry P51800000591 (verified) → move one to canonical, delete the other
  2. Unit registration records (102): re-point building_id + building_unit_id to canonical equivalents
     (overlapping units matched by normalised wing letter + unit_number)
  3. registration_party_contact_matches (1): re-point building_id to canonical
  4. Building units — New Parser (713 units):
       • 628 overlap with canonical → set canonical_status='merged', record redirect in metadata
       • up to 85 unique → move to canonical building (update building_id + building_name)
  5. Duplicate buildings: annotate metadata with merged_into info (kept for audit trail)
  6. "Kalpataru Radiance A" SAMPLE records: only the 3 SAMPLE registration records exist;
     the building record itself is left as a named artifact (no contacts, no relationships)

Dry-run by default. Writing requires --apply --real-ok.
Revert: --revert (dry-run) or --revert --apply --real-ok.
"""

from __future__ import annotations
from _db import psql

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"

PHASE = "6.23"
CANONICAL_NAME = "Kalpataru Radiance"
DUPLICATE_NAMES = ("Kalpataru Radiance New Parser", "Kalpataru Radiance A")

# IDs looked up at runtime
CANONICAL_ID: str = ""
DUPLICATE_IDS: list[str] = []

def read_env(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    return ""
def q(v) -> str:
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"

def load_ids() -> bool:
    global CANONICAL_ID, DUPLICATE_IDS
    code, out = psql(f"SELECT id::text, name FROM buildings WHERE name IN ({q(CANONICAL_NAME)}, {q(DUPLICATE_NAMES[0])}, {q(DUPLICATE_NAMES[1])}) ORDER BY name;")
    if code:
        print(f"ERROR loading building IDs: {out}")
        return False
    id_map: dict[str, str] = {}
    for line in out.splitlines():
        parts = line.split("|", 1)
        if len(parts) == 2:
            id_map[parts[1].strip()] = parts[0].strip()
    CANONICAL_ID = id_map.get(CANONICAL_NAME, "")
    DUPLICATE_IDS = [id_map.get(n, "") for n in DUPLICATE_NAMES]
    if not CANONICAL_ID:
        print(f"ERROR: canonical building {CANONICAL_NAME!r} not found.")
        return False
    return True

def preview(apply: bool) -> None:
    """Print a dry-run summary of what will change."""
    dup_ids_sql = "(" + ",".join(q(d) for d in DUPLICATE_IDS if d) + ")"

    sections = [
        ("RERA profiles in duplicates",
         f"SELECT b.name, rp.rera_registration_number, rp.verification_status FROM rera_project_profiles rp JOIN buildings b ON b.id=rp.building_id WHERE rp.building_id IN {dup_ids_sql}"),
        ("Reg records to re-point (by wing overlap)",
         f"""SELECT b.name bld, SUBSTRING(bu.wing FROM '([A-Da-d])$') ltr, bu.unit_number, urr.doc_number, urr.transaction_category
               FROM unit_registration_records urr
               JOIN building_units bu ON bu.id=urr.building_unit_id
               JOIN buildings b ON b.id=urr.building_id
              WHERE urr.building_id IN {dup_ids_sql}
              LIMIT 20"""),
        ("Unique units (only in duplicates, no match in canonical)",
         f"""SELECT b.name, bu.wing, bu.unit_number, count(urr.id) regs
               FROM building_units bu
               JOIN buildings b ON b.id=bu.building_id
               LEFT JOIN unit_registration_records urr ON urr.building_unit_id=bu.id
              WHERE bu.building_id IN {dup_ids_sql}
                AND NOT EXISTS (
                  SELECT 1 FROM building_units main
                  WHERE main.building_id={q(CANONICAL_ID)}
                    AND SUBSTRING(main.wing FROM '([A-D])$') = bu.wing
                    AND main.unit_number = bu.unit_number
                )
              GROUP BY b.name, bu.wing, bu.unit_number
              ORDER BY b.name, bu.wing, bu.unit_number"""),
        ("Contact matches to re-point",
         f"SELECT building_id::text, match_status, match_strength FROM registration_party_contact_matches WHERE building_id IN {dup_ids_sql}"),
    ]

    for title, sql in sections:
        _, out = psql(sql)
        lines = [l for l in out.splitlines() if l]
        print(f"\n── {title} ({len(lines)} rows) ──")
        for l in lines[:15]:
            print(f"   {l}")
        if len(lines) > 15:
            print(f"   … {len(lines)-15} more")

    print()
    if not apply:
        print("DRY RUN — no changes made. Pass --apply --real-ok to execute.")

def merge_sql() -> str:
    """Build the single-transaction SQL that does the full merge."""
    dup_ids_sql = "(" + ",".join(q(d) for d in DUPLICATE_IDS if d) + ")"
    merged_meta = json.dumps({"canonical_status": "merged", "merged_into_id": CANONICAL_ID,
                               "merged_into_name": CANONICAL_NAME, "merged_phase": PHASE})

    return f"""
BEGIN;

-- ── 1. RERA profiles ──────────────────────────────────────────────────────
-- Move first duplicate RERA profile to canonical (if canonical doesn't have it yet)
UPDATE rera_project_profiles
   SET building_id = {q(CANONICAL_ID)}
 WHERE building_id IN {dup_ids_sql}
   AND rera_registration_number = 'P51800000591'
   AND NOT EXISTS (
     SELECT 1 FROM rera_project_profiles
      WHERE building_id = {q(CANONICAL_ID)}
        AND rera_registration_number = 'P51800000591'
   );

-- Delete the remaining duplicate RERA row for P51800000591
DELETE FROM rera_project_profiles
 WHERE building_id IN {dup_ids_sql}
   AND rera_registration_number = 'P51800000591';

-- ── 2. Unit registration records ──────────────────────────────────────────
-- Re-point each duplicate record to the matching canonical unit (by wing letter + unit_number)
-- Records with doc_numbers already in canonical are left pointing to duplicates temporarily;
-- after dedup below they'll be cleaned up.
UPDATE unit_registration_records urr
   SET building_id     = {q(CANONICAL_ID)},
       building_unit_id = main_bu.id
  FROM building_units np_bu
  JOIN building_units main_bu
    ON main_bu.building_id = {q(CANONICAL_ID)}
   AND SUBSTRING(main_bu.wing FROM '([A-D])$') = np_bu.wing
   AND main_bu.unit_number = np_bu.unit_number
 WHERE np_bu.building_id IN {dup_ids_sql}
   AND urr.building_unit_id = np_bu.id;

-- Flag any registration records that are now duplicate doc_numbers within the canonical building.
-- We use UPDATE (not DELETE) so review_item FKs stay intact.
-- The "loser" (from New Parser source) gets verification_status='duplicate_doc_number'.
UPDATE unit_registration_records
   SET verification_status = 'duplicate_doc_number'
 WHERE id IN (
   SELECT id FROM (
     SELECT id,
            ROW_NUMBER() OVER (
              PARTITION BY building_id, doc_number
              ORDER BY CASE source_label WHEN 'IGR .xls export (CTS 260)' THEN 0 ELSE 1 END,
                       created_at
            ) rn
       FROM unit_registration_records
      WHERE building_id = {q(CANONICAL_ID)}
   ) ranked WHERE rn > 1
 );

-- ── 3. Contact party matches ───────────────────────────────────────────────
UPDATE registration_party_contact_matches
   SET building_id = {q(CANONICAL_ID)}
 WHERE building_id IN {dup_ids_sql};

-- ── 4a. Move unique units (only in duplicates) to canonical ───────────────
UPDATE building_units
   SET building_id    = {q(CANONICAL_ID)},
       building_name  = {q(CANONICAL_NAME)},
       metadata       = metadata || {q(json.dumps({"moved_from_phase": PHASE, "original_source": "duplicate_building"}))}::jsonb
 WHERE building_id IN {dup_ids_sql}
   AND canonical_status = 'active'
   AND NOT EXISTS (
     SELECT 1 FROM building_units main
      WHERE main.building_id = {q(CANONICAL_ID)}
        AND SUBSTRING(main.wing FROM '([A-D])$') = building_units.wing
        AND main.unit_number = building_units.unit_number
   );

-- ── 4b. Archive overlapping units still in duplicates ─────────────────────
UPDATE building_units
   SET canonical_status = 'duplicate',
       metadata         = metadata || {q(json.dumps({"merged_into_building": CANONICAL_NAME, "merged_phase": PHASE}))}::jsonb
 WHERE building_id IN {dup_ids_sql}
   AND canonical_status = 'active';

-- ── 5. Mark duplicate buildings in metadata ───────────────────────────────
UPDATE buildings
   SET metadata = metadata || {q(merged_meta)}::jsonb
 WHERE id IN {dup_ids_sql};

COMMIT;
"""

def counts_sql() -> str:
    return f"""
SELECT 'rera_project_profiles' t,    count(*) FROM rera_project_profiles    WHERE building_id = {q(CANONICAL_ID)}
UNION ALL
SELECT 'unit_registration_records',  count(*) FROM unit_registration_records WHERE building_id = {q(CANONICAL_ID)}
UNION ALL
SELECT 'reg_party_contact_matches',  count(*) FROM registration_party_contact_matches WHERE building_id = {q(CANONICAL_ID)}
UNION ALL
SELECT 'building_units_active',      count(*) FROM building_units WHERE building_id = {q(CANONICAL_ID)} AND canonical_status='active'
UNION ALL
SELECT 'building_units_merged',      count(*) FROM building_units WHERE building_id = {q(CANONICAL_ID)} AND canonical_status='duplicate'
UNION ALL
SELECT 'dup_units_still_active',     count(*) FROM building_units WHERE building_id IN ({",".join(q(d) for d in DUPLICATE_IDS if d)}) AND canonical_status='active'
UNION ALL
SELECT 'dup_rera_still_in_dups',     count(*) FROM rera_project_profiles WHERE building_id IN ({",".join(q(d) for d in DUPLICATE_IDS if d)});
"""

def revert_sql() -> str:
    dup_ids_sql = "(" + ",".join(q(d) for d in DUPLICATE_IDS if d) + ")"
    return f"""
BEGIN;

-- Restore RERA profile(s) moved to canonical back to New Parser building
UPDATE rera_project_profiles
   SET building_id = (SELECT id FROM buildings WHERE name={q(DUPLICATE_NAMES[0])} LIMIT 1)
 WHERE building_id = {q(CANONICAL_ID)}
   AND rera_registration_number = 'P51800000591';

-- Un-archive merged units in duplicates
UPDATE building_units
   SET canonical_status = 'active',
       metadata = metadata - 'merged_into_building' - 'merged_phase'
 WHERE building_id IN {dup_ids_sql}
   AND canonical_status = 'duplicate';

-- Move unique units back from canonical to New Parser
UPDATE building_units
   SET building_id = (SELECT id FROM buildings WHERE name={q(DUPLICATE_NAMES[0])} LIMIT 1),
       building_name = {q(DUPLICATE_NAMES[0])},
       metadata = metadata - 'moved_from_phase' - 'original_source'
 WHERE building_id = {q(CANONICAL_ID)}
   AND metadata->>'original_source' = 'duplicate_building';

-- Move registration records back to duplicate units
-- (best-effort: re-point by doc_number to any matching unit in duplicates)
UPDATE unit_registration_records urr
   SET building_id = np_bu.building_id,
       building_unit_id = np_bu.id
  FROM building_units np_bu
  JOIN buildings b ON b.id = np_bu.building_id
 WHERE b.name IN ({q(DUPLICATE_NAMES[0])}, {q(DUPLICATE_NAMES[1])})
   AND urr.building_id = {q(CANONICAL_ID)}
   AND urr.raw_context->>'source' = 'igr_xls_kalpataru_new_parser_v1'
   AND SUBSTRING(np_bu.wing FROM '([A-D])$') IS NOT NULL
   AND np_bu.unit_number = urr.unit_text;

-- Restore contact party matches
UPDATE registration_party_contact_matches
   SET building_id = (SELECT id FROM buildings WHERE name={q(DUPLICATE_NAMES[0])} LIMIT 1)
 WHERE building_id = {q(CANONICAL_ID)}
   AND raw_context->>'source' = 'igr_xls_kalpataru_new_parser_v1';

-- Un-annotate duplicate buildings
UPDATE buildings
   SET metadata = metadata - 'canonical_status' - 'merged_into_id' - 'merged_into_name' - 'merged_phase'
 WHERE id IN {dup_ids_sql};

COMMIT;
"""

def main() -> int:
    ap = argparse.ArgumentParser(description="Merge Kalpataru Radiance building variants into one canonical record.")
    ap.add_argument("--apply", action="store_true", help="Write changes (also needs --real-ok)")
    ap.add_argument("--real-ok", action="store_true", help="Confirm real data write")
    ap.add_argument("--revert", action="store_true", help="Revert the merge (dry-run unless --apply --real-ok)")
    args = ap.parse_args()

    if not load_ids():
        return 1

    print(f"Canonical building : {CANONICAL_NAME!r}  id={CANONICAL_ID}")
    for name, bid in zip(DUPLICATE_NAMES, DUPLICATE_IDS):
        status = bid if bid else "NOT FOUND (already deleted?)"
        print(f"Duplicate building : {name!r}  id={status}")

    if args.revert:
        if not (args.apply and args.real_ok):
            print("\nREVERT dry-run (would undo the merge):")
            _, c = psql(counts_sql())
            print(c)
            print("\nPass --revert --apply --real-ok to execute the revert.")
            return 0
        print("\nExecuting revert …")
        code, out = psql(revert_sql())
        if code:
            print(f"ERROR: {out}")
            return 1
        _, c = psql(counts_sql())
        print("After revert:\n" + c)
        return 0

    print()
    preview(apply=args.apply and args.real_ok)

    if not (args.apply and args.real_ok):
        return 0

    print("\nExecuting merge …")
    code, out = psql(merge_sql())
    if code:
        print(f"ERROR: {out}")
        return 1

    _, c = psql(counts_sql())
    print("After merge:\n" + c)
    print("\nDone. The two duplicate buildings remain in the buildings table (annotated in metadata)")
    print("but all their data has been consolidated into 'Kalpataru Radiance'.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
