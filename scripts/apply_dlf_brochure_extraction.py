#!/usr/bin/env python3
"""
MIS Phase B — Apply brochure extraction to canonical tables.

Guarded by vw_brochure_apply_readiness.ready_to_apply = true.
All approved configs must exist before this runs.

What it does (--apply only):
  1. INSERT DLF Westpark into buildings (skips if already exists by name+developer)
  2. UPDATE building_units.configuration_type where tower+unit_number match a config's typical_floors

Usage:
  python scripts/apply_dlf_brochure_extraction.py          # dry-run: show what would change
  python scripts/apply_dlf_brochure_extraction.py --apply  # write to DB
  python scripts/apply_dlf_brochure_extraction.py --revert # remove the building row (units untouched)
"""

import sys
import argparse
import psycopg2
from pathlib import Path


def get_conn():
    env = {}
    env_path = Path(__file__).parent.parent / "docker" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "localhost"),
        port=int(env.get("POSTGRES_PORT", 5432)),
        dbname=env.get("POSTGRES_DB", "realdeal_os"),
        user=env.get("POSTGRES_USER", "realdeal_admin"),
        password=env.get("POSTGRES_PASSWORD", ""),
    )


DLF_BUILDING = {
    "name": "DLF The Westpark",
    "developer": "DLF",
    "project_name": "DLF The Westpark Phase 1",
    "address_line_1": "Off New Link Road",
    "locality": "Andheri West",
    "city": "Mumbai",
    "state": "Maharashtra",
    "postal_code": "400053",
    "notes": "RERA PR1181012500079. Towers 02–05, 40 floors each.",
}


def check_readiness(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT ready_to_apply, gate_reason FROM vw_brochure_apply_readiness WHERE project_name LIKE '%Westpark%'")
        row = cur.fetchone()
    if not row:
        print("ERROR: No Westpark extraction found in staging.", file=sys.stderr)
        sys.exit(1)
    return row[0], row[1]


def get_configs(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT configuration_type, tower_code, unit_position, bhk,
                   carpet_area_sqft, carpet_area_sqm, typical_floors
            FROM brochure_unit_config_staging buc
            JOIN brochure_extractions be ON be.id = buc.extraction_id
            WHERE be.project_name LIKE '%Westpark%'
              AND buc.review_decision = 'approved'
            ORDER BY tower_code, unit_position, configuration_type
        """)
        return cur.fetchall()


def apply(conn, dry_run):
    ready, reason = check_readiness(conn)
    if not ready:
        print(f"BLOCKED: {reason}")
        print("Run review_dlf_brochure_extraction.py --approve-all first.")
        sys.exit(1)

    with conn.cursor() as cur:
        # 1. Insert building
        cur.execute("SELECT id FROM buildings WHERE name = %s AND developer = %s",
                    (DLF_BUILDING["name"], DLF_BUILDING["developer"]))
        existing = cur.fetchone()
        if existing:
            building_id = existing[0]
            print(f"  Building already exists: {building_id}")
        else:
            print(f"  {'[DRY]' if dry_run else '[INSERT]'} buildings: {DLF_BUILDING['name']}")
            if not dry_run:
                cur.execute("""
                    INSERT INTO buildings (name, developer, project_name, address_line_1,
                                          locality, city, state, postal_code, notes)
                    VALUES (%(name)s, %(developer)s, %(project_name)s, %(address_line_1)s,
                            %(locality)s, %(city)s, %(state)s, %(postal_code)s, %(notes)s)
                    RETURNING id
                """, DLF_BUILDING)
                building_id = cur.fetchone()[0]
                print(f"    → id: {building_id}")
            else:
                building_id = None

        # 2. Update configuration_type on building_units
        configs = get_configs(conn)
        unit_updates = 0
        for cfg_type, tower_code, unit_pos, bhk, carpet, carpet_sqm, floors in configs:
            # Match units by tower_code (wing) and unit_number (position)
            cur.execute("""
                SELECT id, unit_number, wing, floor FROM building_units
                WHERE building_id = %s
                  AND (wing = %s OR unit_number LIKE %s)
                  AND unit_number LIKE %s
            """, (building_id, tower_code, f"{tower_code}%", f"%{unit_pos}"))
            units = cur.fetchall()
            if units:
                print(f"  {'[DRY]' if dry_run else '[UPDATE]'} {cfg_type}: {len(units)} unit(s)")
                if not dry_run:
                    cur.execute("""
                        UPDATE building_units SET configuration_type = %s
                        WHERE id = ANY(%s)
                    """, (cfg_type, [u[0] for u in units]))
                unit_updates += len(units)
            else:
                print(f"  [SKIP] {cfg_type}: no matching units in building_units (units not yet imported)")

        if not dry_run:
            conn.commit()
            print(f"\n✓ Applied: 1 building row, {unit_updates} unit configuration_type updates")
        else:
            print(f"\nDRY RUN complete — {unit_updates} unit(s) would be updated")
            print("Re-run with --apply to write.")


def revert(conn, dry_run):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM buildings WHERE name = %s AND developer = %s",
                    (DLF_BUILDING["name"], DLF_BUILDING["developer"]))
        row = cur.fetchone()
        if not row:
            print("Building not found — nothing to revert.")
            return
        building_id = row[0]

        cur.execute("SELECT COUNT(*) FROM building_units WHERE building_id = %s", (building_id,))
        unit_count = cur.fetchone()[0]
        print(f"  {'[DRY]' if dry_run else '[DELETE]'} buildings row: {building_id} ({unit_count} linked units would lose building_id)")

        if not dry_run:
            cur.execute("DELETE FROM buildings WHERE id = %s", (building_id,))
            conn.commit()
            print("  ✓ Reverted")
        else:
            print("  Re-run with --apply to execute.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    p.add_argument("--revert", action="store_true")
    args = p.parse_args()

    conn = get_conn()

    if args.revert:
        revert(conn, dry_run=not args.apply)
    else:
        apply(conn, dry_run=not args.apply)

    conn.close()


if __name__ == "__main__":
    main()
