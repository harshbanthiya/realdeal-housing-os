#!/usr/bin/env python3
"""Final Kalpataru XLS/parser/Cockpit alignment audit.

Read-only. Compares:
  1. the exact XLS files supplied by the operator,
  2. the refined parser outputs in exports/igr_kalpataru_timelines, and
  3. the live Cockpit DB unit registry / staged IGR rows.

The goal is to identify whether Cockpit-only/extra units are true missed
apartments, parser-cleanups, or DB pollution from nearby buildings / bad unit
normalization.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

SCRIPTS = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import parse_kalpataru_radiance_xls_timeline as parser_mod  # noqa: E402


ENV_FILE = PROJECT_ROOT / "docker" / ".env"
OUTPUT_DIR = PROJECT_ROOT / "exports" / "igr_kalpataru_timelines"
EVENTS_CSV = OUTPUT_DIR / "kalpataru_radiance_events.csv"
BUILDING_NAME = "Kalpataru Radiance"
EXPECTED_PER_FLOOR = {"A": 5, "B": 6, "C": 6, "D": 6}
DEFAULT_XLS_FILES = [
    Path("/Users/sheeed/Downloads/SearchResult3 (3).xls"),
    Path("/Users/sheeed/Downloads/SearchResult3.xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (1).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (2).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (3).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (4).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (5).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (6).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (7).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (8).xls"),
]


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    return ""


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


def expected_positions() -> set[str]:
    out = set()
    for wing, per_floor in EXPECTED_PER_FLOOR.items():
        for floor in range(1, 32):
            for pos in range(1, per_floor + 1):
                out.add(f"{wing}-{floor}-{pos}")
    return out


def derive_position_key(wing: str | None, unit: str | None) -> str:
    letter = tower_letter(wing)
    raw = digits(unit)
    if not (letter and raw):
        return ""
    candidates: list[tuple[int, int]] = []
    if len(raw) >= 4:
        candidates.append((int(raw[:-2]), int(raw[-2:])))
    elif len(raw) == 3:
        candidates.append((int(raw[:-1]), int(raw[-1:])))
        candidates.append((int(raw[:-2]), int(raw[-2:])))
    elif len(raw) == 2:
        candidates.append((int(raw[:-1]), int(raw[-1:])))
    for floor, pos in candidates:
        if 1 <= floor <= 31 and 1 <= pos <= EXPECTED_PER_FLOOR.get(letter, 0):
            return f"{letter}-{floor}-{pos}"
    return ""


def raw_apartment_key(wing: str | None, unit: str | None) -> str:
    letter = tower_letter(wing)
    raw = digits(unit)
    return f"{letter}-{raw}" if letter and raw else ""


def expected_raw_keys() -> set[str]:
    out = set()
    for wing, per_floor in EXPECTED_PER_FLOOR.items():
        for floor in range(1, 32):
            for pos in range(1, per_floor + 1):
                out.add(f"{wing}-{floor}{pos}")
    return out


def classify_xls_row(row: dict[str, str]) -> dict[str, Any]:
    desc = row.get("propertydescription", "")
    tower, _, _, tower_reason = parser_mod.detect_tower(desc)
    prop = parser_mod.parse_property(desc, tower)
    target, reason = parser_mod.is_target_building(desc, tower)
    signals = parser_mod.building_signals(desc, tower_reason)
    status = "excluded"
    parsed_key = ""
    if target and prop.get("unit_number"):
        status = "target_event"
        parsed_key = f"{tower}-{prop['unit_number']}"
    elif target:
        status = "target_no_unit"
    elif signals["has_kalpataru_or_radiance"] or signals["has_cts_260_5a"] or (
        signals["tower_society_signals"] and signals["address_signals"]
    ):
        status = "review"
    return {
        "xls_source_file": Path(row.get("_source_file", "")).name,
        "internal_document_number": row.get("internaldocumentnumber", ""),
        "doc_number": row.get("docno", ""),
        "registration_date": row.get("registrationdate", ""),
        "docname": row.get("docname", ""),
        "parser_status": status,
        "parser_reason": reason,
        "parser_tower": tower or "",
        "parser_unit_number": prop.get("unit_number") or "",
        "parser_possible_wings": ",".join(prop.get("possible_wings") or []),
        "parser_apartment_key": parsed_key,
        "has_kalpataru_or_radiance": signals["has_kalpataru_or_radiance"],
        "has_cts_260_5a": signals["has_cts_260_5a"],
        "address_signals": ";".join(signals["address_signals"]),
        "tower_society_signals": ";".join(signals["tower_society_signals"]),
        "project_level": signals["project_level"],
        "property_description": desc,
    }


def write_csv(path: Path, rows: Iterable[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def load_xls_classifications(files: list[Path]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    classified = []
    by_internal = {}
    seen = set()
    for file in files:
        for row in parser_mod.read_rows(file):
            internal = row.get("internaldocumentnumber") or "|".join(
                [row.get("srocode", ""), row.get("docno", ""), row.get("registrationdate", "")]
            )
            if internal in seen:
                continue
            seen.add(internal)
            item = classify_xls_row(row)
            classified.append(item)
            if item["internal_document_number"]:
                by_internal[item["internal_document_number"]] = item
    return classified, by_internal


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit XLS/parser/Cockpit alignment for Kalpataru.")
    ap.add_argument("files", nargs="*", help="Specific XLS files. Defaults to the 10 operator-supplied files.")
    ap.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = ap.parse_args()

    files = [Path(f).expanduser().resolve() for f in args.files] if args.files else [p.resolve() for p in DEFAULT_XLS_FILES]
    classified_xls, xls_by_internal = load_xls_classifications(files)
    parser_events = list(csv.DictReader(EVENTS_CSV.open(encoding="utf-8")))
    parser_event_docs = {row["doc_number"] for row in parser_events}
    parser_event_keys = {row["apartment_key"] for row in parser_events}

    db_units_rows = run_psql(
        f"""
        select coalesce(bu.id::text,''), coalesce(bu.wing,''), coalesce(bu.unit_number,'')
          from building_units bu
          join buildings b on b.id = bu.building_id
         where b.name = '{BUILDING_NAME}' and bu.canonical_status = 'active';
        """
    )
    db_units = [
        {
            "building_unit_id": bid,
            "db_wing": wing,
            "db_unit_number": unit,
            "db_raw_key": raw_apartment_key(wing, unit),
            "db_position_key": derive_position_key(wing, unit),
        }
        for bid, wing, unit in db_units_rows
    ]
    db_unit_ids = {u["building_unit_id"] for u in db_units}

    db_records_rows = run_psql(
        f"""
        select coalesce(r.id::text,''), coalesce(r.building_unit_id::text,''),
               coalesce(bu.wing,''), coalesce(bu.unit_number,''),
               coalesce(r.wing_text,''), coalesce(r.unit_text,''), coalesce(r.doc_number,''),
               coalesce(r.raw_context->>'internal_doc',''), coalesce(r.registration_date::text,''),
               coalesce(r.document_type,''), coalesce(r.transaction_category,''),
               left(regexp_replace(coalesce(r.property_description_raw,''), E'[\\t\\n\\r]+', ' ', 'g'), 300)
          from unit_registration_records r
          join buildings b on b.id = r.building_id
          left join building_units bu on bu.id = r.building_unit_id
         where b.name = '{BUILDING_NAME}' and r.raw_context->>'source' = 'igr_xls_kalpataru';
        """
    )
    records_by_unit_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in db_records_rows:
        record_id, unit_id, bu_wing, bu_unit, wing_text, unit_text, doc, internal, reg_date, doc_type, category, desc = row
        rec = {
            "record_id": record_id,
            "building_unit_id": unit_id,
            "db_wing": bu_wing,
            "db_unit_number": bu_unit,
            "db_raw_key": raw_apartment_key(bu_wing, bu_unit),
            "db_position_key": derive_position_key(bu_wing, bu_unit),
            "db_wing_text": wing_text,
            "db_unit_text": unit_text,
            "doc_number": doc,
            "internal_document_number": internal,
            "db_registration_date": reg_date,
            "db_document_type": doc_type,
            "db_category": category,
            "db_description_sample": desc,
        }
        records_by_unit_id[unit_id].append(rec)

    expected_raw = expected_raw_keys()
    expected_pos = expected_positions()
    db_raw_keys = {u["db_raw_key"] for u in db_units if u["db_raw_key"]}
    db_pos_keys = {u["db_position_key"] for u in db_units if u["db_position_key"]}

    reverse_rows = []
    for unit in db_units:
        raw_extra = unit["db_raw_key"] not in expected_raw
        position_extra = not unit["db_position_key"] or unit["db_position_key"] not in expected_pos
        if not raw_extra and not position_extra:
            continue
        linked = records_by_unit_id.get(unit["building_unit_id"], []) or [{}]
        for rec in linked:
            internal = rec.get("internal_document_number", "")
            xls = xls_by_internal.get(internal, {})
            row = {
                **unit,
                "raw_extra_vs_simple_inventory": raw_extra,
                "position_extra_vs_physical_inventory": position_extra,
                "doc_number": rec.get("doc_number", ""),
                "internal_document_number": internal,
                "db_registration_date": rec.get("db_registration_date", ""),
                "db_document_type": rec.get("db_document_type", ""),
                "db_wing_text": rec.get("db_wing_text", ""),
                "db_unit_text": rec.get("db_unit_text", ""),
                "in_operator_xls_files": bool(xls),
                "xls_source_file": xls.get("xls_source_file", ""),
                "parser_status_for_xls_row": xls.get("parser_status", ""),
                "parser_reason_for_xls_row": xls.get("parser_reason", ""),
                "parser_apartment_key": xls.get("parser_apartment_key", ""),
                "parser_possible_wings": xls.get("parser_possible_wings", ""),
                "parser_project_level": xls.get("project_level", ""),
                "parser_has_kalpataru_or_radiance": xls.get("has_kalpataru_or_radiance", ""),
                "parser_has_cts_260_5a": xls.get("has_cts_260_5a", ""),
                "db_description_sample": rec.get("db_description_sample", ""),
                "xls_description_sample": (xls.get("property_description") or "")[:300],
            }
            reverse_rows.append(row)

    xls_status_counts = Counter(row["parser_status"] for row in classified_xls)
    reverse_in_xls = [row for row in reverse_rows if row["in_operator_xls_files"]]
    reverse_in_xls_counts = Counter(row["parser_status_for_xls_row"] for row in reverse_in_xls)
    reverse_not_target_examples = [row for row in reverse_in_xls if row["parser_status_for_xls_row"] != "target_event"]
    reverse_target_examples = [row for row in reverse_in_xls if row["parser_status_for_xls_row"] == "target_event"]

    summary = {
        "xls_files": len(files),
        "xls_unique_rows": len(classified_xls),
        "xls_parser_status_counts": dict(sorted(xls_status_counts.items())),
        "parser_events": len(parser_events),
        "parser_units": len(parser_event_keys),
        "parser_events_by_wing": dict(sorted(Counter(row["wing"] for row in parser_events).items())),
        "parser_events_by_category": dict(sorted(Counter(row["category"] for row in parser_events).items())),
        "db_registration_records_source_igr_xls_kalpataru": len(db_records_rows),
        "db_units_raw": len(db_units),
        "db_units_raw_extra_vs_simple_inventory": sum(1 for row in db_units if row["db_raw_key"] not in expected_raw),
        "db_units_physical_positions": len(db_pos_keys),
        "db_physical_positions_extra": len(db_pos_keys - expected_pos),
        "db_physical_positions_missing": len(expected_pos - db_pos_keys),
        "db_extra_or_position_extra_record_rows": len(reverse_rows),
        "db_extra_or_position_extra_rows_found_in_operator_xls": len(reverse_in_xls),
        "db_extra_rows_found_in_xls_by_parser_status": dict(sorted(reverse_in_xls_counts.items())),
        "parser_event_docs_already_in_db_source": len(parser_event_docs & {row[6] for row in db_records_rows}),
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "kalpataru_final_alignment_summary.json"
    reverse_csv = output_dir / "kalpataru_db_extra_units_reverse_xls_trace.csv"
    xls_class_csv = output_dir / "kalpataru_xls_all_rows_parser_classification.csv"
    report_path = output_dir / "KALPATARU_FINAL_XLS_DB_PARSER_ALIGNMENT_REPORT.md"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(reverse_csv, reverse_rows, [
        "db_raw_key", "db_position_key", "db_wing", "db_unit_number", "building_unit_id",
        "raw_extra_vs_simple_inventory", "position_extra_vs_physical_inventory",
        "doc_number", "internal_document_number", "db_registration_date", "db_document_type",
        "db_wing_text", "db_unit_text", "in_operator_xls_files", "xls_source_file",
        "parser_status_for_xls_row", "parser_reason_for_xls_row", "parser_apartment_key",
        "parser_possible_wings", "parser_project_level", "parser_has_kalpataru_or_radiance",
        "parser_has_cts_260_5a", "db_description_sample", "xls_description_sample",
    ])
    write_csv(xls_class_csv, classified_xls, [
        "xls_source_file", "internal_document_number", "doc_number", "registration_date",
        "docname", "parser_status", "parser_reason", "parser_tower", "parser_unit_number",
        "parser_possible_wings", "parser_apartment_key", "has_kalpataru_or_radiance",
        "has_cts_260_5a", "address_signals", "tower_society_signals", "project_level",
        "property_description",
    ])

    report = [
        "# Kalpataru Radiance XLS / Parser / Cockpit Alignment",
        "",
        "## Scope",
        f"- XLS files audited: {len(files)} operator-supplied exports.",
        f"- XLS unique rows: {summary['xls_unique_rows']}.",
        f"- Cockpit DB source checked: `{BUILDING_NAME}` / `igr_xls_kalpataru`.",
        "",
        "## Headline Counts",
        f"- Refined parser target apartment events: {summary['parser_events']} across {summary['parser_units']} units.",
        f"- Parser events by wing: {summary['parser_events_by_wing']}.",
        f"- Parser events by category: {summary['parser_events_by_category']}.",
        f"- Cockpit staged DB registrations: {summary['db_registration_records_source_igr_xls_kalpataru']}.",
        f"- Cockpit active raw unit rows: {summary['db_units_raw']}.",
        f"- Cockpit distinct physical unit positions after cleanup-normalization: {summary['db_units_physical_positions']}.",
        f"- DB physical positions outside A=5/B,C,D=6 x 31 floors: {summary['db_physical_positions_extra']}.",
        f"- Expected physical positions missing from DB: {summary['db_physical_positions_missing']}.",
        "",
        "## XLS Classification",
        f"- All XLS row parser status counts: {summary['xls_parser_status_counts']}.",
        "- `target_event` rows are confident A/B/C/D apartment timeline events.",
        "- `review` rows carry Kalpataru/CTS signals but lack safe apartment assignment.",
        "- `excluded` rows are other buildings, shops/E-wing, Patra/rehab/project-level entries, or weak address-only matches.",
        "",
        "## Reverse DB Extra Check",
        f"- DB extra/position-extra record rows traced: {summary['db_extra_or_position_extra_record_rows']}.",
        f"- Of those, rows found in the operator XLS files: {summary['db_extra_or_position_extra_rows_found_in_operator_xls']}.",
        f"- Parser status for found XLS rows: {summary['db_extra_rows_found_in_xls_by_parser_status']}.",
        "",
        "## Interpretation",
        "- The DB has many raw unit rows that look extra only because the older import preserved inconsistent unit strings (`1001`, `83, Along with 2 Car Parking,`, etc.).",
        "- After physical position normalization, some of those are valid positions, but many linked records are from nearby buildings or project-level/security documents.",
        "- The strongest confirmed problem is not missing unit cells: it is dirty DB registration fields. Many DB rows have the correct raw description but blank `wing_text`, blank `unit_text`, or no `building_unit_id`, so Cockpit cannot attach the event to the unit timeline.",
        "- The refined parser correctly recovers typo-heavy true rows such as `KALAPATRU RADIANCE`, `KALPATARU RESIDENCE`, `KALPATARU RADIANC`, `कल्पतारु`, and `रॅडिअन्स`, while rejecting `The Meadows / द मेडोस` and other nearby buildings.",
        "",
        "## Evidence Files",
        f"- Summary JSON: `{summary_path}`",
        f"- Reverse DB-extra to XLS trace: `{reverse_csv}`",
        f"- Full XLS row classification: `{xls_class_csv}`",
        "- Parser event output: `exports/igr_kalpataru_timelines/kalpataru_radiance_events.csv`",
        "- Cockpit mismatch output: `exports/igr_kalpataru_timelines/kalpataru_cockpit_event_mismatches.csv`",
        "",
        "## Recommended Next Cleanup",
        "1. Do not blindly trust existing `building_units` for Kalpataru; normalize to physical `(tower, floor, stack)` first.",
        "2. Update/re-stage `unit_registration_records` from the refined parser so `wing_text`, `unit_text`, and `building_unit_id` are populated for the 102 confident events.",
        "3. Keep the 14 review rows separate; only two apartment-looking rows lack wing (`75`, `286`) and should not be auto-assigned.",
        "4. Quarantine old DB rows whose source description matches negative building names (`द मेडोस`, `The Meadows`, Esquire/Oberoi/etc.) even if a generic wing letter was parsed.",
    ]
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"report: {report_path}")
    print(f"reverse_trace: {reverse_csv}")
    print(f"xls_classification: {xls_class_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
