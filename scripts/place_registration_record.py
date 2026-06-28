#!/usr/bin/env python3
"""
Assign a registration record to its canonical building unit (sets building_unit_id).

Dry-run by default — no DB writes unless --apply is passed.

Usage:
  python scripts/place_registration_record.py --record-id UUID --wing A --unit-number 291
  python scripts/place_registration_record.py --record-id UUID --wing A --unit-number 291 --apply
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import run_psql, sql_literal

UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)


def main() -> int:
    ap = argparse.ArgumentParser(description="Assign a registration record to its canonical unit.")
    ap.add_argument("--record-id", required=True, help="UUID of unit_registration_records row")
    ap.add_argument("--wing", required=True, help="Single letter, e.g. A, B, C")
    ap.add_argument("--unit-number", required=True, help="Flat number digits, e.g. 291")
    ap.add_argument("--apply", action="store_true", help="Write to DB (default: dry-run)")
    args = ap.parse_args()

    if not UUID_RE.match(args.record_id):
        print("ERROR: --record-id must be a UUID"); return 1
    wing = args.wing.strip().upper()
    if not re.match(r'^[A-Z]$', wing):
        print("ERROR: --wing must be a single letter"); return 1
    unit = args.unit_number.strip().lstrip(',').strip()
    if not re.match(r'^\d{2,6}$', unit):
        print(f"ERROR: --unit-number must be 2-6 digits, got: {unit!r}"); return 1

    record_id = args.record_id.strip()

    # Verify the record exists and get its building_id
    code, out = run_psql(f"""
        SELECT id::text, building_id::text,
               doc_number, document_type, registration_year::text
        FROM unit_registration_records
        WHERE id = {sql_literal(record_id)}
        LIMIT 1;
    """)
    rows = [l for l in out.strip().splitlines() if '|' in l]
    if code != 0 or not rows:
        print(f"ERROR: record {record_id[:8]}… not found\n{out}"); return 1
    rec_id, building_id, doc_num, doc_type, year = [x.strip() for x in rows[0].split('|')]

    # Find the matching building_unit
    code2, out2 = run_psql(f"""
        SELECT bu.id::text, bu.wing, bu.unit_number, b.name
        FROM building_units bu
        JOIN buildings b ON b.id = bu.building_id
        WHERE bu.building_id = {sql_literal(building_id)}
          AND UPPER(TRIM(bu.wing)) LIKE '%' || {sql_literal(wing)}
          AND TRIM(bu.unit_number) = {sql_literal(unit)}
          AND bu.canonical_status = 'active'
        LIMIT 1;
    """)
    unit_rows = [l for l in out2.strip().splitlines() if '|' in l]
    if code2 != 0 or not unit_rows:
        print(f"No active building unit found for wing={wing} unit={unit} in building {building_id[:8]}…")
        print("Check: the wing letter and flat number must match an existing building_units row.")
        return 1
    unit_id, wing_full, unit_num, bname = [x.strip() for x in unit_rows[0].split('|')]

    print(f"record  : {doc_num} ({doc_type}, {year})")
    print(f"unit    : {wing_full} flat {unit_num} — {bname}")
    print(f"unit_id : {unit_id}")

    if not args.apply:
        print(f"DRY RUN : would set building_unit_id={unit_id} on record {record_id[:8]}…  (pass --apply to write)")
        return 0

    code3, out3 = run_psql(f"""
        UPDATE unit_registration_records
           SET building_unit_id = {sql_literal(unit_id)}::uuid,
               updated_at = now()
         WHERE id = {sql_literal(record_id)}::uuid
         RETURNING id::text;
    """)
    if code3 == 0 and record_id[:8] in out3:
        print(f"placed  : record {record_id[:8]}… → unit {unit_id[:8]}…")
        return 0
    print(f"ERROR: update failed\n{out3}"); return 1


if __name__ == "__main__":
    sys.exit(main())
