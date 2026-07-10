#!/usr/bin/env python3
"""Load consolidated MyGate Tower D residents into canonical tables.

Reuses the consolidation from consolidate_towerd_mygate.py. Idempotent: keyed on
contacts.metadata->>'mygate_key' so re-runs don't duplicate. All relationships
land as 'pending_review' (review-gated). Ambiguous ('?') units are skipped.

Operator decision (2026-07-09): create the wing-D building_units rows that MyGate
shows occupied but the seed lacked, then attach residents to all clean units.

    python3 scripts/load_towerd_mygate.py --dry-run   # print stage counts, no write
    python3 scripts/load_towerd_mygate.py             # execute
"""
from __future__ import annotations

import sys

from _db import lit, run_psql
from consolidate_towerd_mygate import (BUILDING_ID, WING, XLSX, best_phone_match,
                                       consolidate, norm_name)
import json
from pathlib import Path
from consolidate_towerd_mygate import RAW


def stage_rows():
    raw = [json.loads(l) for l in RAW.read_text().splitlines() if l.strip()]
    contacts = json.loads(XLSX.read_text())
    units, _ambiguous = consolidate(raw)
    rows, seen = [], set()
    for unit, u in units.items():
        for role, name in u["people"]:
            rel = "owner" if role.startswith("owner") else "tenant"
            key = f"{unit}|{norm_name(name)}|{rel}"
            if key in seen:  # same person+unit+rel (e.g. listed as Owner and Owner Family)
                continue
            seen.add(key)
            _, phone, score = best_phone_match(name, contacts)
            rows.append({
                "unit": unit, "floor": u["floor"], "role": role, "rel": rel,
                "name": name, "key": key,
                "phone": phone if score >= 0.85 else "",
            })
    return rows


def main():
    dry = "--dry-run" in sys.argv
    rows = stage_rows()
    values = ",\n".join(
        f"({lit(r['unit'])},{lit(r['floor'])},{lit(r['role'])},{lit(r['rel'])},"
        f"{lit(r['name'])},{lit(r['key'])},{lit(r['phone'])})"
        for r in rows)

    b = lit(BUILDING_ID)
    sql = f"""
BEGIN;
CREATE TEMP TABLE stage(unit text, floor text, role text, rel text,
                        name text, key text, phone text) ON COMMIT DROP;
INSERT INTO stage VALUES
{values};

-- 1. create wing-D units MyGate shows occupied but the seed lacked
INSERT INTO building_units (building_id, building_name, wing, unit_number, floor,
                            canonical_status, confidence, metadata)
SELECT DISTINCT {b}::uuid, 'Imperial Heights', '{WING}', s.unit, s.floor,
       'active', 0.6, jsonb_build_object('source','mygate_towerd','seeded_from','mygate')
FROM stage s
WHERE NOT EXISTS (SELECT 1 FROM building_units bu
                  WHERE bu.building_id={b}::uuid AND bu.wing='{WING}'
                        AND bu.unit_number=s.unit);

-- 2. find-or-create one contact per (unit, person, role)
INSERT INTO contacts (full_name, contact_type, source, canonical_status, is_test,
                      phone_primary, whatsapp_number, tags, metadata)
SELECT s.name, s.rel, 'mygate_towerd', 'active', false,
       NULLIF(s.phone,''), NULLIF(s.phone,''),
       ARRAY['imperial_heights','tower_d','mygate'],
       jsonb_build_object('mygate_key',s.key,'mygate_role',s.role,'mygate_unit',s.unit)
FROM (SELECT DISTINCT ON (key) * FROM stage ORDER BY key) s
WHERE NOT EXISTS (SELECT 1 FROM contacts c WHERE c.metadata->>'mygate_key'=s.key);

-- 3. relationships (pending_review), owner_family->owner / tenant_family->tenant
INSERT INTO contact_property_relationships
       (contact_id, building_id, building_unit_id, relationship_type,
        relationship_status, confidence, raw_context, notes)
SELECT c.id, {b}::uuid, bu.id, s.rel, 'pending_review', 0.6,
       jsonb_build_object('source','mygate_towerd','mygate_role',s.role,
                          'unit',s.unit,'floor',s.floor),
       'MyGate Tower D residents import 2026-07-09'
FROM stage s
JOIN contacts c ON c.metadata->>'mygate_key'=s.key
JOIN building_units bu ON bu.building_id={b}::uuid AND bu.wing='{WING}'
                       AND bu.unit_number=s.unit
WHERE NOT EXISTS (SELECT 1 FROM contact_property_relationships r
                  WHERE r.contact_id=c.id AND r.building_unit_id=bu.id
                        AND r.relationship_type=s.rel);

-- 4. phone as a contact_method (WhatsApp group export)
INSERT INTO contact_methods (contact_id, method_type, raw_value, normalized_value,
                             label, is_primary, validation_status)
SELECT c.id, 'whatsapp', s.phone, s.phone, 'MyGate/Tower D WhatsApp', true, 'unverified'
FROM stage s
JOIN contacts c ON c.metadata->>'mygate_key'=s.key
WHERE s.phone<>'' AND NOT EXISTS (
      SELECT 1 FROM contact_methods m WHERE m.contact_id=c.id AND m.raw_value=s.phone);

SELECT 'units_created',  count(*) FROM building_units
   WHERE building_id={b}::uuid AND wing='{WING}' AND metadata->>'seeded_from'='mygate';
SELECT 'contacts_total', count(*) FROM contacts WHERE metadata->>'mygate_unit' IS NOT NULL;
SELECT 'rels_total',     count(*) FROM contact_property_relationships r
   JOIN contacts c ON c.id=r.contact_id WHERE c.metadata->>'mygate_unit' IS NOT NULL;
SELECT 'phones_total',   count(*) FROM contact_methods m
   JOIN contacts c ON c.id=m.contact_id WHERE c.metadata->>'mygate_unit' IS NOT NULL
        AND m.label='MyGate/Tower D WhatsApp';
{"ROLLBACK;" if dry else "COMMIT;"}
"""
    code, out = run_psql(sql)
    print(("DRY-RUN (rolled back)\n" if dry else "COMMITTED\n") + out)
    if code != 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
