#!/usr/bin/env python3
"""Load the full MyGate resident directory into canonical Kalpataru Radiance tables.

Mirrors load_towerd_mygate.py. Idempotent: contacts keyed on
metadata->>'mygate_ruid' (stable MyGate user id) so re-runs never duplicate.
All relationships land 'pending_review' (review-gated).

Behaviour, per operator request 2026-07-09:
  * match each MyGate flat to its Kalpataru building_unit (wing letter + flat digits);
  * create the units MyGate shows occupied but the IGR-seeded DB lacked (~426);
  * where a resident's name matches an existing Kalpataru-linked contact (unique
    match only), REUSE that contact — mix, don't duplicate — else create new.

    python3 scripts/load_kalpataru_mygate.py --dry-run   # counts, rolled back
    python3 scripts/load_kalpataru_mygate.py             # commit
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from _db import lit, run_psql

BUILDING_ID = "f63d75ab-2ef9-48a9-afe2-cab3c4283283"
BUILDING_NAME = "Kalpataru Radiance"
DUMP = Path(__file__).resolve().parents[1] / "captures" / "mygate_directory"
STAMP = "MyGate directory import 2026-07-09"


def norm_name(n: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", (n or "").lower())).strip()


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def rel_of(rtypename: str) -> str:
    return "tenant" if "tenant" in (rtypename or "").lower() else "owner"


def load_residents():
    """-> list of dicts, one per (resident, flat)."""
    rows = []
    for f in sorted(DUMP.glob("building_*.json")):
        d = json.loads(f.read_text())
        w = d["buildingname"].strip()
        if w not in ("A", "B", "C", "D"):
            continue
        for flat in d.get("flats") or []:
            fd = digits(flat["fname"])
            if not fd:
                continue
            for r in flat.get("residents") or []:
                ruid = str(r["r_user_id"])
                rows.append({
                    "ruid": ruid,
                    "name": r["rname"].strip(),
                    "nname": norm_name(r["rname"]),
                    "rel": rel_of(r["rtypename"]),
                    "mygate_role": r["rtypename"],
                    "wing": w,
                    "flat": str(flat["fname"]).strip(),
                    "flatd": fd,
                    "floor": str(flat.get("floor") or ""),
                })
    # collapse exact dup (ruid, unit, rel) — a person listed twice for one flat
    seen, out = set(), []
    for r in rows:
        k = (r["ruid"], r["wing"], r["flatd"], r["rel"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def existing_unit_keys() -> set[tuple[str, str]]:
    _, out = run_psql(f"""
        SELECT DISTINCT regexp_replace(upper(wing),'.*([A-Z])\\s*$','\\1') w,
               regexp_replace(unit_number,'\\D','','g') d
        FROM building_units WHERE building_id='{BUILDING_ID}';""")
    keys = set()
    for line in out.strip().splitlines():
        p = [x.strip() for x in line.split("|")]
        if len(p) == 2 and p[1]:
            keys.add((p[0], p[1]))
    return keys


def name_to_contact() -> dict[str, str]:
    """Unique normalized-name -> contact_id, scoped to Kalpataru-linked contacts."""
    _, out = run_psql(f"""
        SELECT DISTINCT c.id::text, c.full_name
        FROM contacts c
        JOIN contact_property_relationships r ON r.contact_id=c.id
        JOIN building_units bu ON bu.id=r.building_unit_id
        WHERE bu.building_id='{BUILDING_ID}'
          AND c.source <> 'mygate';""")
    # Scope to PRE-EXISTING contacts only (source<>'mygate'). Two traps here:
    #   * include this loader's own contacts and the map grows each commit, so a
    #     name flips from unique-match to ambiguous (or vice versa) and residents
    #     re-point at a different contact -> fresh rels every run.
    #   * filter on mygate_ruid IS NULL instead and the name-matched winners
    #     (pre-existing contacts we stamp a ruid onto) drop out on the next run.
    # source<>'mygate' keeps the winners and excludes the loader-created rows.
    by = {}
    for line in out.strip().splitlines():
        p = line.split("|", 1)
        if len(p) != 2:
            continue
        cid, name = p[0].strip(), norm_name(p[1])
        by.setdefault(name, set()).add(cid)
    return {n: next(iter(ids)) for n, ids in by.items() if len(ids) == 1}


def main():
    dry = "--dry-run" in sys.argv
    residents = load_residents()
    have_units = existing_unit_keys()
    name_map = name_to_contact()

    # resolve each resident's existing-contact link (unique Kalpataru name match)
    for r in residents:
        r["match_cid"] = name_map.get(r["nname"], "")

    new_units = sorted({(r["wing"], r["flat"], r["flatd"], r["floor"])
                        for r in residents if (r["wing"], r["flatd"]) not in have_units})
    matched_names = sum(1 for r in residents if r["match_cid"])

    print(f"residents={len(residents)}  new_units={len(new_units)}  "
          f"name_matched_to_existing={matched_names}  distinct_ruids={len({r['ruid'] for r in residents})}")

    unit_vals = ",\n".join(
        f"('KALPATARU RADIANCE  {w}',{lit(flat)},{lit(fl)})" for w, flat, _, fl in new_units) or "(NULL,NULL,NULL)"

    res_vals = ",\n".join(
        f"({lit(r['ruid'])},{lit(r['name'])},{lit(r['rel'])},{lit(r['mygate_role'])},"
        f"{lit(r['wing'])},{lit(r['flatd'])},{lit(r['match_cid'])})"
        for r in residents)

    b = lit(BUILDING_ID)
    sql = f"""
BEGIN;
CREATE TEMP TABLE new_units(wing text, unit_number text, floor text) ON COMMIT DROP;
INSERT INTO new_units VALUES {unit_vals};
DELETE FROM new_units WHERE wing IS NULL;

CREATE TEMP TABLE stage(ruid text, name text, rel text, mygate_role text,
                        wing_l text, flatd text, match_cid text) ON COMMIT DROP;
INSERT INTO stage VALUES
{res_vals};

-- 1. create units MyGate shows occupied but the IGR seed lacked
INSERT INTO building_units (building_id, building_name, wing, unit_number, floor,
                            canonical_status, confidence, metadata)
SELECT {b}::uuid, {lit(BUILDING_NAME)}, n.wing, n.unit_number, NULLIF(n.floor,''),
       'active', 0.6, jsonb_build_object('source','mygate','seeded_from','mygate')
FROM new_units n
WHERE NOT EXISTS (
    SELECT 1 FROM building_units bu WHERE bu.building_id={b}::uuid
      AND regexp_replace(upper(bu.wing),'.*([A-Z])\\s*$','\\1')=regexp_replace(upper(n.wing),'.*([A-Z])\\s*$','\\1')
      AND regexp_replace(bu.unit_number,'\\D','','g')=regexp_replace(n.unit_number,'\\D','','g'));

-- 2a. link existing Kalpataru contacts whose name uniquely matched — stamp the ruid
UPDATE contacts c SET metadata = coalesce(c.metadata,'{{}}'::jsonb)
       || jsonb_build_object('mygate_ruid', s.ruid, 'mygate_linked_by','name_match',
                             'mygate_unit', s.wing_l||'-'||s.flatd)
FROM (SELECT DISTINCT ON (ruid) match_cid, ruid, wing_l, flatd FROM stage
      WHERE match_cid<>'' ORDER BY ruid) s
WHERE c.id=s.match_cid::uuid AND coalesce(c.metadata->>'mygate_ruid','')='';

-- 2b. create new contacts for ruids not present and not name-matched
INSERT INTO contacts (full_name, contact_type, source, canonical_status, is_test,
                      tags, metadata)
SELECT s.name, s.rel, 'mygate', 'active', false,
       ARRAY['kalpataru_radiance','mygate'],
       jsonb_build_object('mygate_ruid',s.ruid,'mygate_role',s.mygate_role,
                          'mygate_unit',s.wing_l||'-'||s.flatd)
-- covers pure-new ruids AND name-match "losers" (a namesake claimed the existing
-- contact in 2a), so no resident is dropped for lacking a contact.
FROM (SELECT DISTINCT ON (ruid) ruid, name, rel, mygate_role, wing_l, flatd FROM stage
      ORDER BY ruid) s
WHERE NOT EXISTS (SELECT 1 FROM contacts c WHERE c.metadata->>'mygate_ruid'=s.ruid);

-- 3. canonical unit per (wing letter, flat digits) — earliest row wins
CREATE TEMP TABLE unit_pick ON COMMIT DROP AS
SELECT DISTINCT ON (w,d) id AS unit_id, w, d FROM (
  SELECT id, regexp_replace(upper(wing),'.*([A-Z])\\s*$','\\1') w,
         regexp_replace(unit_number,'\\D','','g') d, created_at
  FROM building_units WHERE building_id={b}::uuid) t
WHERE d<>'' ORDER BY w,d,created_at,id;   -- id tie-breaks dup IGR units -> deterministic across runs

-- 4. relationships (pending_review), joined contact(by ruid) -> canonical unit
INSERT INTO contact_property_relationships
       (contact_id, building_id, building_unit_id, relationship_type,
        relationship_status, confidence, raw_context, notes)
SELECT c.id, {b}::uuid, up.unit_id, s.rel, 'pending_review', 0.6,
       jsonb_build_object('source','mygate','mygate_role',s.mygate_role,
                          'wing',s.wing_l,'flat',s.flatd,'mygate_ruid',s.ruid),
       {lit(STAMP)}
FROM stage s
JOIN contacts c ON c.metadata->>'mygate_ruid'=s.ruid
JOIN unit_pick up ON up.w=s.wing_l AND up.d=s.flatd
WHERE NOT EXISTS (
    SELECT 1 FROM contact_property_relationships r
    WHERE r.contact_id=c.id AND r.building_unit_id=up.unit_id
      AND r.relationship_type=s.rel);

SELECT 'units_created', count(*) FROM building_units
   WHERE building_id={b}::uuid AND metadata->>'seeded_from'='mygate';
SELECT 'contacts_mygate', count(*) FROM contacts WHERE metadata->>'mygate_ruid' IS NOT NULL;
SELECT 'contacts_name_linked', count(*) FROM contacts WHERE metadata->>'mygate_linked_by'='name_match';
SELECT 'rels_mygate', count(*) FROM contact_property_relationships
   WHERE raw_context->>'source'='mygate' AND building_id={b}::uuid;
{"ROLLBACK;" if dry else "COMMIT;"}
"""
    code, out = run_psql(sql)
    print(("DRY-RUN (rolled back)\n" if dry else "COMMITTED\n") + out)
    sys.exit(code)


if __name__ == "__main__":
    main()
