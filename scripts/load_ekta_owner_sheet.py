#!/usr/bin/env python3
"""Load 'Ekta Tripolis Data new.xlsx' (443 flats w/ FLAT DETAILS, CLIENT NAME,
PHONE, EMAIL) into the Ekta Tripolis registry.

Per row:
  1. unit  : normalize FLAT DETAILS (A-102) -> building_units (create missing,
             confidence 0.6, metadata.source='ekta_sheet_2026')
  2. contact: match ANY existing contact by last-10 phone; else create
             (source='ekta_sheet_2026', contact_type='owner')
  3. rel   : contact_property_relationships owner/pending_review (probable,
             NON-confirmed — operator reviews in cockpit), skip if one exists
             for (contact, unit).

Dry-run by default; --apply to write. Never touches confirmed/active rows.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db import run_psql, sql_literal as lit, jsonb_lit  # noqa: E402

SHEET = Path("/Users/sheeed/Downloads/Data of buildings/Ekta Tripolis Data new.xlsx")
BUILDING_ID = "2032514a-adef-4d2f-a12c-6ecf06853243"  # Ekta Tripolis
SOURCE = "ekta_sheet_2026"
PHONE_RE = re.compile(r"(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})")


def q(sql: str) -> list[list[str]]:
    code, out = run_psql(sql)
    if code != 0:
        raise RuntimeError(out)
    return [line.split("|") for line in out.splitlines() if line]


def norm_unit(raw: str) -> str:
    """'A-102', 'A 102', 'a102' -> 'A-102'."""
    m = re.match(r"\s*([A-Da-d])\s*[- ]?\s*(\d{3,4})\s*$", raw or "")
    return f"{m.group(1).upper()}-{m.group(2)}" if m else ""


def phones_of(raw: str) -> list[str]:
    return list(dict.fromkeys(re.sub(r"[\s-]", "", m) for m in PHONE_RE.findall(raw or "")))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    ws = openpyxl.load_workbook(SHEET, read_only=True)["TRIPOLIS"]
    rows = []
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 or not r or len(r) < 5:
            continue
        unit = norm_unit(str(r[1] or ""))
        name = re.sub(r"\s+", " ", str(r[3] or "")).strip()
        phones = phones_of(str(r[4] or ""))
        email = str(r[5] or "").split(";")[0].strip() if len(r) > 5 and r[5] else ""
        config = str(r[2] or "").strip()
        if not unit or not (name or phones):
            continue
        rows.append((unit, config, name, phones, email))
    print(f"sheet_rows_usable: {len(rows)}")

    # existing state
    units = {r[1]: r[0] for r in q(
        f"SELECT id, unit_number FROM building_units WHERE building_id='{BUILDING_ID}'") if len(r) >= 2}
    phone_map = {}
    for r in q("""SELECT contact_id::text, val FROM (
          SELECT id AS contact_id, UNNEST(ARRAY[whatsapp_number, phone_primary, phone_secondary]) AS val FROM contacts
          UNION ALL SELECT contact_id, COALESCE(normalized_value, raw_value) FROM contact_methods
            WHERE method_type IN ('mobile','phone') AND contact_id IS NOT NULL) s
          WHERE val IS NOT NULL AND val <> ''"""):
        if len(r) >= 2:
            key = re.sub(r"\D", "", r[1])[-10:]
            if len(key) == 10 and key not in phone_map:
                phone_map[key] = r[0]

    new_units = new_contacts = matched_contacts = new_rels = 0
    stmts: list[str] = []
    seen_pairs: set[tuple[str, str]] = set()
    for unit, config, name, phones, email in rows:
        # 1. unit
        unit_id = units.get(unit)
        if not unit_id:
            new_units += 1
            unit_id = f"__unit__{unit}"
            stmts.append(
                f"""INSERT INTO building_units (building_id, building_name, unit_number, wing,
                      configuration_type, canonical_status, confidence, metadata)
                    VALUES ('{BUILDING_ID}', 'Ekta Tripolis', {lit(unit)}, {lit(unit[0])},
                      {lit(config) if config else 'NULL'}, 'active', 0.6,
                      {jsonb_lit({'source': SOURCE})})
                    ON CONFLICT DO NOTHING""")
            units[unit] = unit_id
        # 2. contact
        contact_id = next((phone_map[p[-10:]] for p in phones if p[-10:] in phone_map), "")
        if contact_id:
            matched_contacts += 1
        elif name or phones:
            new_contacts += 1
            contact_id = f"__contact__{phones[0] if phones else name}"
            p1 = phones[0] if phones else None
            p2 = phones[1] if len(phones) > 1 else None
            stmts.append(
                f"""INSERT INTO contacts (full_name, contact_type, phone_primary, phone_secondary,
                      whatsapp_number, email, source, status, canonical_status, notes)
                    VALUES ({lit(name or (p1 or 'Unknown'))}, 'owner', {lit(p1)}, {lit(p2)},
                      {lit(p1)}, {lit(email) if email else 'NULL'}, '{SOURCE}', 'active', 'active',
                      {lit(f'Ekta sheet flat {unit} ({config})')})""")
            for p in phones:
                phone_map[p[-10:]] = contact_id
        else:
            continue
        # 3. relationship (probable owner, NON-confirmed)
        if (contact_id, unit) in seen_pairs:
            continue
        seen_pairs.add((contact_id, unit))
        new_rels += 1
        real_c = not contact_id.startswith("__")
        real_u = not str(unit_id).startswith("__")
        c_expr = lit(contact_id) + "::uuid" if real_c else (
            f"(SELECT id FROM contacts WHERE source='{SOURCE}' AND "
            f"(phone_primary={lit(phones[0]) if phones else 'NULL'} OR full_name={lit(name)}) LIMIT 1)")
        u_expr = lit(unit_id) + "::uuid" if real_u else (
            f"(SELECT id FROM building_units WHERE building_id='{BUILDING_ID}' AND unit_number={lit(unit)} LIMIT 1)")
        stmts.append(
            f"""INSERT INTO contact_property_relationships (contact_id, building_id,
                  building_unit_id, relationship_type, relationship_status, confidence,
                  notes, raw_context)
                SELECT {c_expr}, '{BUILDING_ID}', {u_expr}, 'owner', 'pending_review', 0.6,
                  {lit(f'{SOURCE}: flat {unit}, {config}')},
                  {jsonb_lit({'sheet_name': name, 'phones': phones, 'email': email})}
                WHERE NOT EXISTS (
                  SELECT 1 FROM contact_property_relationships r
                  WHERE r.contact_id = {c_expr} AND r.building_unit_id = {u_expr})
                  AND {c_expr} IS NOT NULL AND {u_expr} IS NOT NULL""")

    print(f"units_to_create: {new_units}")
    print(f"contacts_matched_existing: {matched_contacts}")
    print(f"contacts_to_create: {new_contacts}")
    print(f"relationships_to_stage: {new_rels} (owner / pending_review)")
    if not a.apply:
        print("dry_run: true (pass --apply to write)")
        return
    for s in stmts:
        code, out = run_psql(s)
        if code != 0:
            print(f"error: {out[:200]}")
            sys.exit(1)
    print("dry_run: false")
    print("status: ok")


if __name__ == "__main__":
    main()
