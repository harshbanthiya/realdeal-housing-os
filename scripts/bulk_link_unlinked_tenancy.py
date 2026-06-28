#!/usr/bin/env python3
"""
Auto-link unlinked Kalpataru tenancy records to canonical building_units
by parsing wing + flat number out of wing_text / unit_text.

Dry-run by default. Use --apply to write.

Usage:
  python scripts/bulk_link_unlinked_tenancy.py          # show matches
  python scripts/bulk_link_unlinked_tenancy.py --apply  # write to DB
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import run_psql, sql_literal


def parse_wing_unit(wing_t: str, unit_t: str) -> tuple[str | None, str | None]:
    """Extract (wing_letter, unit_number) from raw IGR text fields."""
    text = (wing_t + " " + unit_t).strip()

    # Strip noise tokens that look like letter-digit combos
    text = re.sub(r"Shop\s*No\s*:", "", text, flags=re.I)
    text = re.sub(r"\(WITH[^)]*\)", "", text, flags=re.I)
    text = re.sub(r"\bEMPTY\s+FLAT\b", "", text, flags=re.I)
    text = re.sub(r"\b(ORA|ALLURA|BRILLIANCE)\b", "", text, flags=re.I)
    text = re.sub(r"[,;]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    wing: str | None = None
    unit: str | None = None

    # "Wing C-Allura" / "Wing B-Brilliance" → wing from wing_text prefix
    m = re.search(r"\bWing\s+([A-D])\b", text, re.I)
    if m:
        wing = m.group(1).upper()

    # "Wing - A" / "Wing-A"
    m = re.search(r"\bWing\s*[-–]\s*([A-D])\b", text, re.I)
    if m:
        wing = wing or m.group(1).upper()

    # "[ABCD]-digits" or "[ABCD] digits"   e.g. "C-63", "B-226", "C 61"
    m = re.search(r"\b([A-D])[- ](\d{2,4})\b", text, re.I)
    if m:
        wing = wing or m.group(1).upper()
        unit = unit or m.group(2)

    # "[ABCD]/digits"   "B/306"
    m = re.search(r"\b([A-D])/(\d{2,4})\b", text, re.I)
    if m:
        wing = wing or m.group(1).upper()
        unit = unit or m.group(2)

    # "[ABCD] digits" (space only, like "B 176")
    m = re.search(r"\b([A-D])\s+(\d{2,4})\b", text, re.I)
    if m:
        wing = wing or m.group(1).upper()
        unit = unit or m.group(2)

    # digits then "[ABCD] Wing" / "[ABCD]-Wing"   "101,A wing" / "63, Wing - A" / "181 - A WING"
    m = re.search(r"\b(\d{2,4})\b[^A-Z]*\b([A-D])\s*[-–\s]*\s*Wing\b", text, re.I)
    if m:
        wing = wing or m.group(2).upper()
        unit = unit or m.group(1)

    # digits then "A WING" (no "Wing" keyword, just "A WING" all caps)
    m = re.search(r"\b(\d{2,4})\b.*?\b([A-D])\s+WING\b", text, re.I)
    if m:
        wing = wing or m.group(2).upper()
        unit = unit or m.group(1)

    # If we have a wing but no unit yet, grab the first 2-4 digit number
    if wing and not unit:
        m = re.search(r"\b(\d{2,4})\b", text)
        if m:
            unit = m.group(1)

    # If we have neither, try grabbing any 2-4 digit number (unit only, wing unknown)
    if not wing and not unit:
        m = re.search(r"\b(\d{2,4})\b", text)
        if m:
            unit = m.group(1)

    return wing, unit


def load_unlinked() -> list[dict]:
    _, out = run_psql("""
        SELECT r.id::text, r.doc_number, r.wing_text, r.unit_text,
               r.registration_date::text, b.id::text AS building_id,
               r.tenancy_monthly_rent::text, r.tenancy_start_date::text
        FROM unit_registration_records r
        JOIN buildings b ON b.id = r.building_id
        WHERE b.name ILIKE '%Kalpataru%Radiance%'
          AND COALESCE(r.transaction_category, registration_category(r.document_type)) = 'tenancy'
          AND r.building_unit_id IS NULL
          AND r.doc_number NOT LIKE 'SAMPLE%%'
          AND COALESCE(r.wing_text, '') NOT ILIKE '%%Patra%%'
          AND COALESCE(r.wing_text, '') NOT ILIKE '%%MHADA%%'
        ORDER BY r.registration_date;
    """)
    rows = []
    for line in out.strip().splitlines():
        p = line.split("|")
        if len(p) < 8:
            continue
        rid, doc, wing_t, unit_t, date, bid, rent, start = [x.strip() for x in p[:8]]
        wing, unit = parse_wing_unit(wing_t, unit_t)
        rows.append({
            "id": rid, "doc": doc, "wing_t": wing_t, "unit_t": unit_t,
            "date": date[:10], "building_id": bid,
            "rent": rent, "start": start,
            "wing": wing, "unit": unit,
        })
    return rows


def find_unit(building_id: str, wing: str, unit: str) -> str | None:
    """Return building_unit id if exactly one active match found."""
    _, out = run_psql(f"""
        SELECT id::text FROM building_units
        WHERE building_id = {sql_literal(building_id)}::uuid
          AND UPPER(TRIM(wing)) LIKE '%%' || {sql_literal(wing.upper())}
          AND TRIM(unit_number) = {sql_literal(unit)}
          AND canonical_status = 'active'
        LIMIT 2;
    """)
    ids = [l.strip() for l in out.strip().splitlines() if l.strip()]
    return ids[0] if len(ids) == 1 else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Bulk-link unlinked Kalpataru tenancy records.")
    ap.add_argument("--apply", action="store_true", help="Write to DB (default: dry-run)")
    args = ap.parse_args()

    records = load_unlinked()
    print(f"Unlinked tenancy records (excl. Patra Chawl): {len(records)}\n")

    placed = []
    no_unit_found = []
    no_parse = []

    for r in records:
        if not r["wing"] or not r["unit"]:
            no_parse.append(r)
            continue

        unit_id = find_unit(r["building_id"], r["wing"], r["unit"])
        if not unit_id:
            no_unit_found.append(r)
            continue

        placed.append({**r, "unit_id": unit_id})

    # Print results
    if placed:
        print(f"=== CAN AUTO-LINK ({len(placed)}) ===")
        for r in placed:
            action = "APPLY" if args.apply else "DRY-RUN"
            print(f"  [{action}] doc {r['doc']:<8}  {r['wing']}-{r['unit']:<5}  "
                  f"unit_id {r['unit_id'][:8]}…  rent {r['rent'] or '—':>8}  {r['date']}")

    if no_unit_found:
        print(f"\n=== PARSED BUT NO MATCHING UNIT ({len(no_unit_found)}) ===")
        for r in no_unit_found:
            print(f"  doc {r['doc']:<8}  parsed → {r['wing']}-{r['unit']}  "
                  f"(unit not in building_units)  raw: {r['unit_t']!r}")

    if no_parse:
        print(f"\n=== CANNOT PARSE WING/UNIT ({len(no_parse)}) — need review board ===")
        for r in no_parse:
            print(f"  doc {r['doc']:<8}  unit_text={r['unit_t']!r}  wing_text={r['wing_t']!r}  "
                  f"rent {r['rent'] or '—'}  {r['date']}")

    print(f"\nSummary: {len(placed)} can link  |  {len(no_unit_found)} parsed but unit missing  |  {len(no_parse)} need review")

    if not args.apply:
        print("\nDry-run — pass --apply to write.")
        return 0

    # Apply
    ok = 0
    for r in placed:
        code, out = run_psql(f"""
            UPDATE unit_registration_records
               SET building_unit_id = {sql_literal(r['unit_id'])}::uuid,
                   updated_at = now()
             WHERE id = {sql_literal(r['id'])}::uuid
             RETURNING id::text;
        """)
        if code == 0 and r["id"][:8] in out:
            print(f"  linked doc {r['doc']} → unit {r['unit_id'][:8]}…")
            ok += 1
        else:
            print(f"  ERROR doc {r['doc']}: {out.strip()}")

    print(f"\nLinked {ok}/{len(placed)} records.")
    return 0 if ok == len(placed) else 1


if __name__ == "__main__":
    sys.exit(main())
