#!/usr/bin/env python3
"""Collapse duplicate unit_registration_records rows (same building_id + doc_number).

For each dup group, keeps the highest-priority source row as the keeper,
merges any non-null fields from the losers into it, then deletes the losers.
Finally adds a UNIQUE constraint to prevent future collisions.

Source priority (highest first):
  4  IGR bulk ingest 2020-2026
  3  Refined Kalpataru Radiance XLS parser (confident A/B/C/D events)
  2  IGR eSearch results list 2026 (CTS 260/5A)
  1  IGR .xls export (CTS 260)
  0  anything else

Usage:
  python scripts/dedup_registration_records.py            # dry run
  python scripts/dedup_registration_records.py --apply --real-ok
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db import run_psql, lit

SOURCE_PRIORITY = {
    "IGR bulk ingest 2020-2026": 4,
    "Refined Kalpataru Radiance XLS parser (confident A/B/C/D events)": 3,
    "IGR eSearch results list 2026 (CTS 260/5A)": 2,
    "IGR .xls export (CTS 260)": 1,
}

# Fields merged via COALESCE (keeper's value wins if non-null; otherwise take first non-null loser)
MERGE_FIELDS = [
    "document_type", "registration_date", "sro_office",
    "unit_text", "floor_text", "area_text", "property_description_raw",
    "consideration_amount", "market_value", "stamp_duty", "registration_fee",
    "tenancy_start_date", "tenancy_end_date", "tenancy_monthly_rent", "tenancy_deposit",
    "parse_confidence",
]

WING_SHORT = {"A", "B", "C", "D"}


def _priority(source_label: str) -> int:
    return SOURCE_PRIORITY.get(source_label or "", 0)


def _resolve_wing(keeper_wing: str | None, loser_wings: list[str | None]) -> str | None:
    """Trust the keeper's wing; only expand short letter to full name if a loser confirms it."""
    if not keeper_wing:
        # keeper has no wing — take first non-null from losers
        return next((w for w in loser_wings if w), None)
    if keeper_wing not in WING_SHORT:
        # keeper already has a full name — keep it, don't let losers override
        return keeper_wing
    # keeper has a short letter ("A"/"B"/"C"/"D") — expand only if a loser agrees
    for w in loser_wings:
        if w and w not in WING_SHORT and w.startswith(f"Wing {keeper_wing}"):
            return w
    return keeper_wing  # keep short letter, no confirming expansion found


def fetch_dup_groups(building_id: str) -> list[list[dict]]:
    """Return list of groups; each group is a list of row dicts sorted by priority desc."""
    import json as _json
    code, out = run_psql(f"""
        SELECT row_to_json(r) FROM (
          SELECT id, doc_number, source_label, wing_text,
                 document_type, registration_date, sro_office,
                 unit_text, floor_text, area_text, property_description_raw,
                 consideration_amount, market_value, stamp_duty, registration_fee,
                 tenancy_start_date, tenancy_end_date, tenancy_monthly_rent, tenancy_deposit,
                 parse_confidence
          FROM unit_registration_records
          WHERE building_id = {lit(building_id)}
            AND doc_number IN (
              SELECT doc_number FROM unit_registration_records
              WHERE building_id = {lit(building_id)}
              GROUP BY doc_number HAVING COUNT(*) > 1
            )
          ORDER BY doc_number,
            CASE source_label
              WHEN 'IGR bulk ingest 2020-2026' THEN 4
              WHEN 'Refined Kalpataru Radiance XLS parser (confident A/B/C/D events)' THEN 3
              WHEN 'IGR eSearch results list 2026 (CTS 260/5A)' THEN 2
              WHEN 'IGR .xls export (CTS 260)' THEN 1
              ELSE 0
            END DESC,
            id
        ) r
    """)
    if code != 0:
        print(f"ERROR fetching dups: {out}"); sys.exit(1)

    groups: dict[str, list[dict]] = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        row = _json.loads(line)
        groups.setdefault(row["doc_number"], []).append(row)

    return list(groups.values())


def merge_group(rows: list[dict]) -> tuple[dict, list[str]]:
    """Return (merged_keeper, [loser_ids])."""
    keeper = dict(rows[0])  # highest priority
    losers = rows[1:]

    # Merge non-null fields from losers into keeper
    for loser in losers:
        for field in MERGE_FIELDS:
            if keeper.get(field) is None and loser.get(field) is not None:
                keeper[field] = loser[field]

    # Wing: trust keeper's wing; only expand short letter if a loser confirms it
    keeper["wing_text"] = _resolve_wing(
        keeper.get("wing_text"),
        [r.get("wing_text") for r in losers],
    )

    return keeper, [r["id"] for r in losers]


def build_sql(groups: list[list[dict]], building_id: str) -> list[str]:
    stmts: list[str] = []
    for rows in groups:
        keeper, loser_ids = merge_group(rows)

        # UPDATE keeper with merged values
        set_clauses = []
        for field in MERGE_FIELDS + ["wing_text"]:
            val = keeper.get(field)
            if val is not None:
                set_clauses.append(f"{field} = {lit(val)}")
        if set_clauses:
            stmts.append(
                f"UPDATE unit_registration_records SET {', '.join(set_clauses)}"
                f" WHERE id = {lit(keeper['id'])};"
            )

        # Re-parent children before DELETE (avoids FK violations)
        for lid in loser_ids:
            stmts.append(
                f"UPDATE unit_registration_parties"
                f" SET unit_registration_record_id = {lit(keeper['id'])}"
                f" WHERE unit_registration_record_id = {lit(lid)};"
            )
            stmts.append(
                f"UPDATE unit_registration_review_items"
                f" SET unit_registration_record_id = {lit(keeper['id'])}"
                f" WHERE unit_registration_record_id = {lit(lid)};"
            )

        # DELETE losers (children already re-parented; CASCADE has nothing left)
        ids_sql = ", ".join(lit(i) for i in loser_ids)
        stmts.append(f"DELETE FROM unit_registration_records WHERE id IN ({ids_sql});")

    return stmts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    args = ap.parse_args()

    # Get building id
    code, building_id = run_psql(
        "SELECT id FROM buildings WHERE name ILIKE '%kalpataru%radiance%'"
        " ORDER BY created_at LIMIT 1"
    )
    if code != 0 or not building_id.strip():
        print("ERROR: building not found"); return 1
    building_id = building_id.strip()

    groups = fetch_dup_groups(building_id)
    wing_conflicts = sum(
        1 for g in groups
        if len({r.get("wing_text") for r in g} - {None}) > 1
    )
    total_to_delete = sum(len(g) - 1 for g in groups)

    print(f"Duplicate groups : {len(groups)}")
    print(f"Wing conflicts   : {wing_conflicts}")
    print(f"Rows to delete   : {total_to_delete}")
    print()

    # Show wing conflicts
    if wing_conflicts:
        print("Wing conflict resolution (keeper wing → chosen):")
        for rows in groups:
            wings = [r.get("wing_text") for r in rows]
            unique = {w for w in wings if w}
            if len(unique) > 1:
                keeper, _ = merge_group(rows)
                print(f"  doc={rows[0]['doc_number']:6}  sources={[r['source_label'][:30] for r in rows]}")
                print(f"    wings seen: {wings}  → kept: {keeper['wing_text']}")
        print()

    stmts = build_sql(groups, building_id)

    if not args.apply or not args.real_ok:
        print(f"Dry run — {len(stmts)} SQL statements would execute.")
        print("Re-run with --apply --real-ok to commit.")
        return 0

    # Execute in a single transaction
    sql = "BEGIN;\n" + "\n".join(stmts) + "\nCOMMIT;"
    code, out = run_psql(sql)
    if code != 0:
        print(f"ERROR — rolled back:\n{out}"); return 1
    print(f"Deleted {total_to_delete} duplicate rows.")

    # Add unique constraint
    code2, out2 = run_psql(
        "ALTER TABLE unit_registration_records"
        " ADD CONSTRAINT unit_registration_records_building_doc_uniq"
        " UNIQUE (building_id, doc_number);"
    )
    if code2 != 0:
        # Already exists or other issue — check
        if "already exists" in out2:
            print("Unique constraint already present — skipped.")
        else:
            print(f"WARNING: could not add unique constraint:\n{out2}")
    else:
        print("Added UNIQUE (building_id, doc_number) constraint.")

    # Final counts
    _, counts = run_psql(f"""
        SELECT COUNT(*) AS total, COUNT(DISTINCT doc_number) AS unique_docs,
               COUNT(*) FILTER (WHERE transaction_category = 'tenancy') AS ll_rows
        FROM unit_registration_records
        WHERE building_id = {lit(building_id)}
    """)
    total, unique_docs, ll = counts.strip().split("|")
    print(f"\nFinal: {total} rows / {unique_docs} unique docs / {ll} L&L records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
