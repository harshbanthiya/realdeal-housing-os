#!/usr/bin/env python3
"""Compare parsed Kalpataru timeline CSV with the Cockpit unit registry state.

Read-only. The script uses the local Postgres DB to see what Cockpit currently
has in `building_units` and `unit_registration_records`, then compares that to
`exports/igr_kalpataru_timelines/kalpataru_radiance_events.csv`.
"""

from __future__ import annotations
from _db import read_env_value

import argparse
import csv
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS_CSV = PROJECT_ROOT / "exports" / "igr_kalpataru_timelines" / "kalpataru_radiance_events.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "exports" / "igr_kalpataru_timelines"
BUILDING_NAME = "Kalpataru Radiance"
EXPECTED_PER_FLOOR = {"A": 5, "B": 6, "C": 6, "D": 6}
def run_psql(sql: str) -> list[list[str]]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not (user and password and db_name):
        raise RuntimeError("Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env")
    cmd = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql", "-U", user, "-d", db_name, "-At", "-F", "\t",
    ]
    result = subprocess.run(cmd, input=sql, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return [line.split("\t") for line in result.stdout.splitlines() if line]

def tower_letter(wing: str | None) -> str:
    match = re.search(r"([A-Z])\s*$", (wing or "").upper())
    return match.group(1) if match else ""

def digits(unit: str | None) -> str:
    return re.sub(r"\D", "", unit or "")

def unit_key(wing: str | None, unit: str | None) -> str:
    return f"{tower_letter(wing)}-{digits(unit)}"

def expected_units() -> set[str]:
    out = set()
    for wing, per_floor in EXPECTED_PER_FLOOR.items():
        for floor in range(1, 32):
            for pos in range(1, per_floor + 1):
                out.add(f"{wing}-{floor}{pos}")
    return out

def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})

def main() -> int:
    parser = argparse.ArgumentParser(description="Compare parsed Kalpataru events with Cockpit DB state.")
    parser.add_argument("--events-csv", default=str(DEFAULT_EVENTS_CSV))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    events_csv = Path(args.events_csv)
    output_dir = Path(args.output_dir)
    parsed_events = list(csv.DictReader(events_csv.open(encoding="utf-8")))
    parsed_units = {row["apartment_key"] for row in parsed_events}

    db_unit_rows = run_psql(
        f"""
        select coalesce(bu.id::text,''), coalesce(bu.wing,''), coalesce(bu.unit_number,''),
               count(r.id)::text
          from building_units bu
          join buildings b on b.id = bu.building_id
          left join unit_registration_records r on r.building_unit_id = bu.id and r.verification_status <> 'rejected'
         where b.name = '{BUILDING_NAME}' and bu.canonical_status = 'active'
         group by bu.id, bu.wing, bu.unit_number
         order by bu.wing, bu.unit_number;
        """
    )
    db_units = {
        unit_key(wing, unit): {"building_unit_id": bid, "wing": wing, "unit_number": unit, "registration_count": count}
        for bid, wing, unit, count in db_unit_rows
        if unit_key(wing, unit) != "-"
    }

    db_record_rows = run_psql(
        f"""
        select coalesce(r.id::text,''), coalesce(r.wing_text,''), coalesce(r.unit_text,''),
               coalesce(r.doc_number,''), coalesce(r.raw_context->>'internal_doc',''),
               coalesce(r.registration_date::text,''), coalesce(r.document_type,''), coalesce(r.transaction_category,''),
               coalesce(r.building_unit_id::text,''),
               left(regexp_replace(coalesce(r.property_description_raw,''), E'[\\t\\n\\r]+', ' ', 'g'), 240)
          from unit_registration_records r
          join buildings b on b.id = r.building_id
         where b.name = '{BUILDING_NAME}' and r.raw_context->>'source' = 'igr_xls_kalpataru';
        """
    )
    db_record_keys = {(tower_letter(wing), digits(unit), doc) for _, wing, unit, doc, *_ in db_record_rows}
    db_records_by_doc = {}
    for row in db_record_rows:
        record_id, wing, unit, doc, internal_doc, reg_date, doc_type, category, building_unit_id, desc = row
        db_records_by_doc.setdefault(doc, []).append({
            "record_id": record_id,
            "db_wing_text": wing,
            "db_unit_text": unit,
            "db_unit_key": unit_key(wing, unit),
            "doc_number": doc,
            "internal_document_number": internal_doc,
            "registration_date": reg_date,
            "document_type": doc_type,
            "category": category,
            "building_unit_id": building_unit_id,
            "db_description_sample": desc,
        })

    event_matches = []
    event_misses = []
    for event in parsed_events:
        key = (event["wing"], digits(event["unit_number"]), event["doc_number"])
        row = {
            "parsed_apartment_key": event["apartment_key"],
            "parsed_wing": event["wing"],
            "parsed_unit_number": event["unit_number"],
            "parsed_registration_date": event["registration_date"],
            "doc_number": event["doc_number"],
            "parsed_document_type": event["document_type"],
            "parsed_category": event["category"],
            "parsed_consideration_amount": event["consideration_amount"],
            "parsed_description_sample": event["property_description_raw"][:240],
        }
        db_same_doc = db_records_by_doc.get(event["doc_number"], [])
        if key in db_record_keys:
            row["match_status"] = "matched_doc_wing_unit"
            event_matches.append(row)
        else:
            row["match_status"] = "doc_exists_but_fields_do_not_match" if db_same_doc else "doc_not_found_in_db_source"
            if db_same_doc:
                row.update(db_same_doc[0])
            event_misses.append(row)

    expected = expected_units()
    db_unit_keys = set(db_units)
    extra_units = [
        {"apartment_key": key, **db_units[key]}
        for key in sorted(db_unit_keys - expected, key=lambda k: (k.split("-")[0], int(k.split("-")[1]) if k.split("-")[1].isdigit() else 99999, k))
    ]
    missing_expected_units = [{"apartment_key": key} for key in sorted(expected - db_unit_keys, key=lambda k: (k.split("-")[0], int(k.split("-")[1])))]
    parsed_missing_from_db = [{"apartment_key": key} for key in sorted(parsed_units - db_unit_keys, key=lambda k: (k.split("-")[0], int(k.split("-")[1])))]

    summary = {
        "building_name": BUILDING_NAME,
        "parsed_events": len(parsed_events),
        "parsed_units": len(parsed_units),
        "db_cockpit_units": len(db_units),
        "expected_units": len(expected),
        "parsed_units_already_in_db": len(parsed_units & db_unit_keys),
        "parsed_units_missing_from_db": len(parsed_missing_from_db),
        "db_units_extra_vs_expected": len(extra_units),
        "db_expected_units_missing": len(missing_expected_units),
        "parsed_events_matching_db_doc_wing_unit": len(event_matches),
        "parsed_events_not_matching_db_doc_wing_unit": len(event_misses),
        "db_units_by_wing": dict(sorted(Counter(k.split("-")[0] for k in db_units).items())),
        "parsed_events_by_wing": dict(sorted(Counter(row["wing"] for row in parsed_events).items())),
        "parsed_events_by_category": dict(sorted(Counter(row["category"] for row in parsed_events).items())),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "kalpataru_cockpit_match_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_csv(
        output_dir / "kalpataru_cockpit_event_mismatches.csv",
        event_misses,
        [
            "match_status", "parsed_apartment_key", "parsed_wing", "parsed_unit_number",
            "parsed_registration_date", "doc_number", "parsed_document_type", "parsed_category",
            "parsed_consideration_amount", "db_wing_text", "db_unit_text", "db_unit_key",
            "building_unit_id", "internal_document_number", "db_description_sample",
            "parsed_description_sample",
        ],
    )
    write_csv(
        output_dir / "kalpataru_cockpit_extra_units.csv",
        extra_units,
        ["apartment_key", "building_unit_id", "wing", "unit_number", "registration_count"],
    )
    write_csv(
        output_dir / "kalpataru_cockpit_missing_expected_units.csv",
        missing_expected_units,
        ["apartment_key"],
    )
    write_csv(
        output_dir / "kalpataru_cockpit_parsed_units_missing_from_db.csv",
        parsed_missing_from_db,
        ["apartment_key"],
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
