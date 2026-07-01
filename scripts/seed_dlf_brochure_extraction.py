#!/usr/bin/env python3
"""
MIS Phase B — Seed DLF Westpark brochure extraction.

Records configuration types read from visual review of Presenter 1.pdf
into brochure_extraction_staging tables. All rows land reviewed=false.

Run review_dlf_brochure_extraction.py to approve and apply to buildings/building_units.

Usage:
  python scripts/seed_dlf_brochure_extraction.py          # dry-run
  python scripts/seed_dlf_brochure_extraction.py --apply
  python scripts/seed_dlf_brochure_extraction.py --cleanup  # remove this seed (dry-run)
  python scripts/seed_dlf_brochure_extraction.py --cleanup --apply
"""

import argparse
import json
import psycopg2
from pathlib import Path

PDF_PATH = "/Volumes/RDH 5TB/RDH DATA 2024/RDH ALL Footage/ALL PROJECTS/DLF Westpark/Presenter 1.pdf"
EXTRACTION_PHASE = "MIS-B"

# ── extracted data (source: visual review of Presenter 1.pdf, 2026-07-01) ─────

EXTRACTION = {
    "project_name": "DLF The Westpark – Phase 1",
    "rera_number": "PR1181012500079",
    "developer_name": "Peegen Builders and Developers Pvt. Ltd. (DLF + Trident Realty)",
    "phase_label": "Phase 1",
    "page_count": 57,
    "towers_found": ["T02", "T03", "T04", "T05"],
}

# tower_code → {floor_count, units_per_typical_floor, typical_floor_ranges,
#               atypical_floors, brochure_page_start}
TOWERS = {
    "T02": {
        "tower_name": "Tower-02",
        "floor_count": 40,
        "units_per_typical_floor": 2,
        "typical_floor_ranges": "3rd–6th, 8th–12th & 14th, 16th–21st, 23rd–28th, 30th–35th (2 units); floors 36–40 single unit only",
        "atypical_floors": [
            {"floors": "7, 15, 22, 29", "type": "refuge_5bhk", "units": "01 only"},
            {"floors": "36, 37, 38", "type": "4bhk_single", "units": "01 only"},
            {"floors": "39–40", "type": "4bhk_duplex", "units": "01 only (lower 39th / upper 40th)"},
        ],
        "brochure_page_start": 6,
    },
    "T03": {
        "tower_name": "Tower-03",
        "floor_count": 40,
        "units_per_typical_floor": 4,
        "typical_floor_ranges": "3–12, 14–38 (units 01/02); 3–12, 14–35, 37–39 (unit 03); 3–6, 8–11, 14, 16–21, 23–28, 30–35, 37–39 (unit 04); floor 36 unit 03 = 4BHK; floors 39–40 units 01/02 = 4BHK duplex",
        "atypical_floors": [
            {"floors": "7, 15, 22, 29", "type": "refuge", "units": "01/02/03 only"},
            {"floors": "12", "type": "refuge_unit04_excluded", "units": "01/02/03 present, 04 absent"},
            {"floors": "13", "type": "refuge_all"},
            {"floors": "36", "type": "refuge_unit03_4bhk", "units": "03=4BHK only (01/02/04 absent)"},
            {"floors": "39–40", "type": "4bhk_duplex", "units": "01 and 02 (lower 39th / upper 40th)"},
        ],
        "brochure_page_start": 20,
    },
    "T04": {
        "tower_name": "Tower-04",
        "floor_count": 40,
        "units_per_typical_floor": 4,
        "typical_floor_ranges": "3–12, 14–38 (unit 01); 3–6, 8–12, 14, 16–21, 23–28, 30–35, 37–39 (units 02/03); floors 36+39–40 single-unit atypical",
        "atypical_floors": [
            {"floors": "7, 15, 22, 29", "type": "refuge_4bhk", "units": "03=4BHK (01/02 absent)"},
            {"floors": "13", "type": "refuge_all"},
            {"floors": "36", "type": "refuge_4bhk_large", "units": "03=4BHK only"},
            {"floors": "39–40", "type": "4bhk_duplex", "units": "01 only (lower 39th / upper 40th)"},
        ],
        "brochure_page_start": 29,
    },
    "T05": {
        "tower_name": "Tower-05",
        "floor_count": 40,
        "units_per_typical_floor": 4,
        "typical_floor_ranges": "3–6, 8–12, 14, 16–21, 23–28, 30–35, 37–38 (unit 01); 3–12, 14–38 (units 02/03); floors 7/15/22/29/36 = refuge studios; floors 39–40 = 4BHK duplex 02+03",
        "atypical_floors": [
            {"floors": "7, 15, 22, 29", "type": "refuge_studio", "units": "01=studio (245sqft, no balcony); 02/03 absent"},
            {"floors": "13", "type": "refuge_all"},
            {"floors": "36", "type": "refuge_studio_large", "units": "01=studio (478sqft); 02/03 absent"},
            {"floors": "39–40", "type": "4bhk_duplex", "units": "02 and 03 (lower 39th / upper 40th)"},
        ],
        "brochure_page_start": 37,
    },
}

# (tower_code, unit_position, is_penthouse, is_refuge_variant) → config data
UNIT_CONFIGS = [
    # ── Tower 02 ──────────────────────────────────────────────────────────────
    # Typical floors (2 units per floor)
    dict(tower_code="T02", unit_position="01", configuration_type="T02-3BHK-01",
         bhk=3, carpet_area_sqft=1260.72, carpet_area_sqm=117.12,
         balcony_sqft=103.99, total_area_sqft=1364.71,
         typical_floors="3–6, 8–12, 14, 16–21, 23–28, 30–35",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=11),

    dict(tower_code="T02", unit_position="02", configuration_type="T02-3BHK-02",
         bhk=3, carpet_area_sqft=1260.72, carpet_area_sqm=117.12,
         balcony_sqft=103.99, total_area_sqft=1364.71,
         typical_floors="3–6, 8–12, 14, 16–21, 23–28, 30–35",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=11),

    # Refuge floors 7, 15, 22, 29 — unit 01 only, 5BHK
    dict(tower_code="T02", unit_position="01", configuration_type="T02-5BHK-01",
         bhk=5, carpet_area_sqft=1825.23, carpet_area_sqm=169.57,
         balcony_sqft=175.69, total_area_sqft=2000.92,
         typical_floors="7, 15, 22, 29",
         is_penthouse=False, is_refuge_variant=True, floor_plan_page=13),

    # Floors 36–38 — unit 01 only, 4BHK (single unit per floor, same floor plan type)
    dict(tower_code="T02", unit_position="01", configuration_type="T02-4BHK-01",
         bhk=4, carpet_area_sqft=2136.46, carpet_area_sqm=198.48,
         balcony_sqft=175.69, total_area_sqft=2312.15,
         typical_floors="36, 37, 38",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=12),

    # Floors 39–40 — unit 01 only, 4BHK Duplex (lower 39th / upper 40th)
    dict(tower_code="T02", unit_position="01", configuration_type="T02-4BHK-DUPLEX-01",
         bhk=4, carpet_area_sqft=2087.62, carpet_area_sqm=193.95,
         balcony_sqft=162.08, total_area_sqft=2249.71,
         typical_floors="39 (lower) + 40 (upper)",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=14),

    # ── Tower 03 ──────────────────────────────────────────────────────────────
    dict(tower_code="T03", unit_position="01", configuration_type="T03-3BHK-01",
         bhk=3, carpet_area_sqft=1255.29, carpet_area_sqm=116.62,
         balcony_sqft=103.99, total_area_sqft=1359.28,
         typical_floors="3–12, 14–38",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=20),

    dict(tower_code="T03", unit_position="02", configuration_type="T03-3BHK-02",
         bhk=3, carpet_area_sqft=1255.29, carpet_area_sqm=116.62,
         balcony_sqft=103.99, total_area_sqft=1359.28,
         typical_floors="3–12, 14–38",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=20),

    dict(tower_code="T03", unit_position="03", configuration_type="T03-3BHK-03",
         bhk=3, carpet_area_sqft=1048.07, carpet_area_sqm=97.37,
         balcony_sqft=78.33, total_area_sqft=1126.40,
         typical_floors="3–12, 14–35, 37–39",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=21),

    # Unit 04 excludes refuge floors 7,15,22,29,36 + floors 12,13 (position is refuge area)
    dict(tower_code="T03", unit_position="04", configuration_type="T03-3BHK-04",
         bhk=3, carpet_area_sqft=1048.07, carpet_area_sqm=97.37,
         balcony_sqft=78.33, total_area_sqft=1126.40,
         typical_floors="3–6, 8–11, 14, 16–21, 23–28, 30–35, 37–39",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=21),

    # Floor 36 — unit 03 only, 4BHK (refuge floor; units 01/02/04 absent)
    dict(tower_code="T03", unit_position="03", configuration_type="T03-4BHK-03",
         bhk=4, carpet_area_sqft=1277.50, carpet_area_sqm=118.69,
         balcony_sqft=78.33, total_area_sqft=1355.83,
         typical_floors="36",
         is_penthouse=False, is_refuge_variant=True, floor_plan_page=22),

    # Floors 39–40 — units 01 and 02, 4BHK Duplex (lower 39th / upper 40th)
    dict(tower_code="T03", unit_position="01", configuration_type="T03-4BHK-DUPLEX-01",
         bhk=4, carpet_area_sqft=2078.77, carpet_area_sqm=193.11,
         balcony_sqft=162.08, total_area_sqft=2240.85,
         typical_floors="39 (lower) + 40 (upper)",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=23),

    dict(tower_code="T03", unit_position="02", configuration_type="T03-4BHK-DUPLEX-02",
         bhk=4, carpet_area_sqft=2078.77, carpet_area_sqm=193.11,
         balcony_sqft=162.08, total_area_sqft=2240.85,
         typical_floors="39 (lower) + 40 (upper)",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=23),

    # ── Tower 04 ──────────────────────────────────────────────────────────────
    dict(tower_code="T04", unit_position="01", configuration_type="T04-3BHK-01",
         bhk=3, carpet_area_sqft=1255.29, carpet_area_sqm=116.62,
         balcony_sqft=103.99, total_area_sqft=1359.28,
         typical_floors="3–12, 14–38",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=30),

    dict(tower_code="T04", unit_position="02", configuration_type="T04-3BHK-02",
         bhk=3, carpet_area_sqft=1084.20, carpet_area_sqm=100.73,
         balcony_sqft=78.33, total_area_sqft=1162.53,
         typical_floors="3–6, 8–12, 14, 16–21, 23–28, 30–35, 37–39",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=30),

    # Unit 03 — same floors as unit 02
    dict(tower_code="T04", unit_position="03", configuration_type="T04-3BHK-03",
         bhk=3, carpet_area_sqft=1048.07, carpet_area_sqm=97.37,
         balcony_sqft=78.33, total_area_sqft=1126.40,
         typical_floors="3–6, 8–12, 14, 16–21, 23–28, 30–35, 37–39",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=31),

    # Refuge floors 7, 15, 22, 29 — unit 03 only, 4BHK
    dict(tower_code="T04", unit_position="03", configuration_type="T04-4BHK-03",
         bhk=4, carpet_area_sqft=1246.20, carpet_area_sqm=115.78,
         balcony_sqft=78.33, total_area_sqft=1324.53,
         typical_floors="7, 15, 22, 29",
         is_penthouse=False, is_refuge_variant=True, floor_plan_page=32),

    # Floor 36 — unit 03 only, 4BHK (larger refuge variant)
    dict(tower_code="T04", unit_position="03", configuration_type="T04-4BHK-03-FL36",
         bhk=4, carpet_area_sqft=1510.37, carpet_area_sqm=140.32,
         balcony_sqft=138.24, total_area_sqft=1648.61,
         typical_floors="36",
         is_penthouse=False, is_refuge_variant=True, floor_plan_page=33),

    # Floors 39–40 — unit 01 only, 4BHK Duplex
    dict(tower_code="T04", unit_position="01", configuration_type="T04-4BHK-DUPLEX-01",
         bhk=4, carpet_area_sqft=2078.79, carpet_area_sqm=193.12,
         balcony_sqft=162.06, total_area_sqft=2240.85,
         typical_floors="39 (lower) + 40 (upper)",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=34),

    # ── Tower 05 ──────────────────────────────────────────────────────────────
    # Unit 01 — excluded on all refuge floors (7, 13, 15, 22, 29, 36)
    dict(tower_code="T05", unit_position="01", configuration_type="T05-3BHK-01",
         bhk=3, carpet_area_sqft=1368.37, carpet_area_sqm=127.13,
         balcony_sqft=99.45, total_area_sqft=1467.82,
         typical_floors="3–6, 8–12, 14, 16–21, 23–28, 30–35, 37–38",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=40),

    # Units 02 and 03 — excluded on floor 13 only
    dict(tower_code="T05", unit_position="02", configuration_type="T05-3BHK-02",
         bhk=3, carpet_area_sqft=1362.13, carpet_area_sqm=126.55,
         balcony_sqft=147.07, total_area_sqft=1509.20,
         typical_floors="3–12, 14–38",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=41),

    dict(tower_code="T05", unit_position="03", configuration_type="T05-3BHK-03",
         bhk=3, carpet_area_sqft=1363.27, carpet_area_sqm=126.66,
         balcony_sqft=147.54, total_area_sqft=1510.81,
         typical_floors="3–12, 14–38",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=41),

    # Refuge floors 7, 15, 22, 29 — unit 01, small studio (no balcony)
    dict(tower_code="T05", unit_position="01", configuration_type="T05-STUDIO-01-REFUGE",
         bhk=1, carpet_area_sqft=245.25, carpet_area_sqm=22.78,
         balcony_sqft=0, total_area_sqft=245.25,
         typical_floors="7, 15, 22, 29",
         is_penthouse=False, is_refuge_variant=True, floor_plan_page=42),

    # Floor 36 — unit 01, larger studio
    dict(tower_code="T05", unit_position="01", configuration_type="T05-STUDIO-01-FL36",
         bhk=1, carpet_area_sqft=477.78, carpet_area_sqm=44.39,
         balcony_sqft=71.70, total_area_sqft=549.48,
         typical_floors="36",
         is_penthouse=False, is_refuge_variant=True, floor_plan_page=43),

    # Floors 39–40 — units 02 and 03, 4BHK Duplex
    dict(tower_code="T05", unit_position="02", configuration_type="T05-4BHK-DUPLEX-02",
         bhk=4, carpet_area_sqft=2277.12, carpet_area_sqm=211.54,
         balcony_sqft=255.68, total_area_sqft=2532.80,
         typical_floors="39 (lower) + 40 (upper)",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=44),

    dict(tower_code="T05", unit_position="03", configuration_type="T05-4BHK-DUPLEX-03",
         bhk=4, carpet_area_sqft=2278.27, carpet_area_sqm=211.64,
         balcony_sqft=256.15, total_area_sqft=2534.42,
         typical_floors="39 (lower) + 40 (upper)",
         is_penthouse=False, is_refuge_variant=False, floor_plan_page=44),
]

# ── DB ────────────────────────────────────────────────────────────────────────

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

# ── seed ──────────────────────────────────────────────────────────────────────

def seed(conn, dry_run):
    print(f"\n{'DRY RUN — ' if dry_run else ''}Seeding DLF Westpark brochure extraction\n")

    with conn.cursor() as cur:
        # check for existing seed
        cur.execute("SELECT id FROM brochure_extractions WHERE rera_number = %s", (EXTRACTION["rera_number"],))
        row = cur.fetchone()
        if row:
            print(f"  Already seeded (extraction id: {row[0]}). Run --cleanup --apply to reset.")
            return

        if not dry_run:
            cur.execute("""
                INSERT INTO brochure_extractions
                  (source_pdf_path, rera_number, developer_name, project_name,
                   phase_label, page_count, towers_found, extraction_method, extraction_phase)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'visual_review',%s)
                RETURNING id
            """, (
                PDF_PATH, EXTRACTION["rera_number"], EXTRACTION["developer_name"],
                EXTRACTION["project_name"], EXTRACTION["phase_label"],
                EXTRACTION["page_count"], EXTRACTION["towers_found"], EXTRACTION_PHASE,
            ))
            extraction_id = cur.fetchone()[0]
        else:
            extraction_id = "<dry-run-id>"

        print(f"  Extraction: {EXTRACTION['project_name']} ({EXTRACTION['rera_number']})")
        print(f"  Towers: {', '.join(EXTRACTION['towers_found'])}")

        tower_ids = {}
        for code, t in TOWERS.items():
            if not dry_run:
                cur.execute("""
                    INSERT INTO brochure_tower_staging
                      (extraction_id, tower_name, tower_code, floor_count,
                       units_per_typical_floor, typical_floor_ranges,
                       atypical_floors, brochure_page_start)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                """, (
                    extraction_id, t["tower_name"], code, t["floor_count"],
                    t["units_per_typical_floor"], t["typical_floor_ranges"],
                    json.dumps(t["atypical_floors"]), t["brochure_page_start"],
                ))
                tower_ids[code] = cur.fetchone()[0]
            else:
                tower_ids[code] = f"<dry-{code}>"
            print(f"  Tower {code}: {t['floor_count']} floors, {t['units_per_typical_floor']} units/floor")

        gates = {}
        for cfg in UNIT_CONFIGS:
            gate = cfg.get("review_gate")
            if gate:
                gates[gate] = gates.get(gate, 0) + 1
            if not dry_run:
                cur.execute("""
                    INSERT INTO brochure_unit_config_staging
                      (extraction_id, tower_staging_id, tower_code, unit_position,
                       configuration_type, bhk, carpet_area_sqft, carpet_area_sqm,
                       balcony_sqft, total_area_sqft, typical_floors,
                       is_penthouse, is_refuge_variant, floor_plan_page,
                       review_gate)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING
                """, (
                    extraction_id, tower_ids[cfg["tower_code"]], cfg["tower_code"],
                    cfg["unit_position"], cfg["configuration_type"], cfg["bhk"],
                    cfg.get("carpet_area_sqft"), cfg.get("carpet_area_sqm"),
                    cfg.get("balcony_sqft"), cfg.get("total_area_sqft"),
                    cfg["typical_floors"], cfg["is_penthouse"], cfg["is_refuge_variant"],
                    cfg["floor_plan_page"], gate,
                ))

        if not dry_run:
            conn.commit()

        print(f"\n  Configs staged : {len(UNIT_CONFIGS)}")
        print(f"  Clean (no gate): {len(UNIT_CONFIGS) - sum(gates.values())}")
        if gates:
            print(f"  Gates raised   :")
            for g, n in gates.items():
                print(f"    {g}: {n}")
        print(f"\n  reviewed=false on all rows — run review_dlf_brochure_extraction.py to approve.")
        if dry_run:
            print("  Re-run with --apply to write.")


def cleanup(conn, dry_run):
    print(f"\n{'DRY RUN — ' if dry_run else ''}Cleanup DLF Westpark brochure seed\n")
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM brochure_extractions WHERE rera_number = %s", (EXTRACTION["rera_number"],))
        row = cur.fetchone()
        if not row:
            print("  Nothing to clean — extraction not found.")
            return
        eid = row[0]
        cur.execute("SELECT COUNT(*) FROM brochure_unit_config_staging WHERE extraction_id = %s", (eid,))
        n_cfg = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM brochure_tower_staging WHERE extraction_id = %s", (eid,))
        n_twr = cur.fetchone()[0]
        print(f"  Would delete: 1 extraction, {n_twr} towers, {n_cfg} configs")
        if not dry_run:
            cur.execute("DELETE FROM brochure_extractions WHERE id = %s", (eid,))
            conn.commit()
            print("  Deleted.")
        else:
            print("  Re-run with --apply to delete.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    p.add_argument("--cleanup", action="store_true")
    args = p.parse_args()
    conn = get_conn()
    if args.cleanup:
        cleanup(conn, not args.apply)
    else:
        seed(conn, not args.apply)
    conn.close()


if __name__ == "__main__":
    main()
