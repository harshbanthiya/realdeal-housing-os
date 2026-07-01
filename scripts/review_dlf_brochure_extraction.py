#!/usr/bin/env python3
"""
MIS Phase B — Brochure extraction review.

Prints the staged DLF Westpark configs for operator approval.
All decisions are reversible until apply_dlf_brochure_extraction.py is run.

Usage:
  python scripts/review_dlf_brochure_extraction.py            # show queue
  python scripts/review_dlf_brochure_extraction.py --approve-all   # approve all configs + extraction
  python scripts/review_dlf_brochure_extraction.py --approve T02-3BHK-01 T02-5BHK-01
  python scripts/review_dlf_brochure_extraction.py --reject  T03-3BHK-04 --note "floor range wrong"
  python scripts/review_dlf_brochure_extraction.py --revert  # reset all decisions to NULL
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


def print_queue(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT buc.configuration_type, buc.tower_code, buc.unit_position,
                   buc.bhk, buc.carpet_area_sqft, buc.balcony_sqft, buc.total_area_sqft,
                   buc.typical_floors, buc.is_refuge_variant, buc.floor_plan_page,
                   buc.review_gate, buc.review_decision
            FROM brochure_unit_config_staging buc
            JOIN brochure_extractions be ON be.id = buc.extraction_id
            WHERE be.project_name LIKE '%Westpark%'
            ORDER BY buc.tower_code, buc.unit_position, buc.configuration_type
        """)
        rows = cur.fetchall()

        cur.execute("""
            SELECT extraction_reviewed, extraction_decision, configs_staged, configs_approved, ready_to_apply
            FROM vw_brochure_extraction_status
            WHERE project_name LIKE '%Westpark%'
        """)
        status = cur.fetchone()

    print("\nDLF Westpark — brochure config review queue")
    print(f"  Extraction reviewed : {status[0]}  decision: {status[1]}")
    print(f"  Configs staged      : {status[2]}  approved: {status[3]}")
    print(f"  Ready to apply      : {status[4]}\n")

    header = f"{'Config':<25} {'BHK':>3} {'Carpet':>8} {'Balcony':>8} {'Total':>8}  {'Floors':<40} {'Refuge':>6}  {'Decision'}"
    print(header)
    print("─" * len(header))
    for row in rows:
        cfg, tower, pos, bhk, carpet, balcony, total, floors, refuge, page, gate, decision = row
        decision_str = decision or ("⚠ " + gate if gate else "pending")
        print(f"{cfg:<25} {bhk:>3} {str(carpet or ''):>8} {str(balcony or ''):>8} {str(total or ''):>8}  {(floors or ''):40} {'✓' if refuge else '':>6}  {decision_str}")

    print(f"\n{len(rows)} configs total")
    if status[4]:
        print("✓ READY — run apply_dlf_brochure_extraction.py --apply to commit to buildings/units")
    else:
        pending = (status[2] or 0) - (status[3] or 0)
        print(f"BLOCKED — {pending} config(s) not yet approved; extraction approved={status[1]}")


def set_decisions(conn, config_types, decision, note):
    with conn.cursor() as cur:
        for cfg in config_types:
            cur.execute("""
                UPDATE brochure_unit_config_staging
                SET review_decision = %s,
                    reviewed = true,
                    review_notes = COALESCE(%s, review_notes)
                WHERE configuration_type = %s
            """, (decision, note, cfg))
            if cur.rowcount == 0:
                print(f"  WARNING: config not found: {cfg}")
            else:
                print(f"  {decision}: {cfg}")
    conn.commit()


def approve_all(conn):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE brochure_unit_config_staging SET review_decision = 'approved', reviewed = true
            WHERE extraction_id = (
                SELECT id FROM brochure_extractions WHERE project_name LIKE '%Westpark%' LIMIT 1
            )
        """)
        n = cur.rowcount
        cur.execute("""
            UPDATE brochure_extractions SET review_decision = 'approved', reviewed = true
            WHERE project_name LIKE '%Westpark%'
        """)
    conn.commit()
    print(f"  Approved {n} configs + extraction")


def revert(conn):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE brochure_unit_config_staging
            SET review_decision = NULL, reviewed = false, review_notes = NULL
            WHERE extraction_id = (
                SELECT id FROM brochure_extractions WHERE project_name LIKE '%Westpark%' LIMIT 1
            )
        """)
        n = cur.rowcount
        cur.execute("""
            UPDATE brochure_extractions
            SET review_decision = NULL, reviewed = false
            WHERE project_name LIKE '%Westpark%'
        """)
    conn.commit()
    print(f"  Reverted {n} configs + extraction to pending")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--approve-all", action="store_true")
    p.add_argument("--approve", nargs="+", metavar="CONFIG_TYPE")
    p.add_argument("--reject", nargs="+", metavar="CONFIG_TYPE")
    p.add_argument("--note", default=None)
    p.add_argument("--revert", action="store_true")
    args = p.parse_args()

    conn = get_conn()

    if args.revert:
        revert(conn)
    elif args.approve_all:
        approve_all(conn)
    elif args.approve:
        set_decisions(conn, args.approve, "approved", args.note)
    elif args.reject:
        set_decisions(conn, args.reject, "rejected", args.note)
    else:
        print_queue(conn)
        return

    print_queue(conn)
    conn.close()


if __name__ == "__main__":
    main()
