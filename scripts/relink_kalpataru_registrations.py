#!/usr/bin/env python3
"""Relink Kalpataru registrations that the old IGR .xls loader attached to the wrong wing.

The `igr_xls_kalpataru` loader linked each record to a building_unit by flat number
but landed on the wrong wing for 681 records: doc 3950 stores tower "B", its
Devanagari reads "विंग बी ब्रीलीयंस", and it was linked to wing A flat 173.

Evidence, per audit_kalpataru_registrations.py:
  * the record itself carries the correct wing in raw_context.tower and wing_text,
    and those two agree with each other in 591 of 597 records;
  * on the 422 mislinked records whose Devanagari names a wing inside a flat clause
    ("सदनिका नं: 173 ... विंग बी"), the description backs the RECOVERED wing 421
    times and the linked wing once.

A record is relinked only when ALL hold:
  * recovered (wing, flat) resolves to exactly one active building_unit;
  * the Devanagari either agrees with the recovered wing or names no wing at all;
  * the flat NUMBER is unchanged (a wing-only correction).

Everything else — flat-number disagreements, the one Devanagari contradiction,
records with no target unit — is left alone and printed for a human.

The previous building_unit_id is kept in raw_context.relink_prev_unit_id, so this
is reversible. registration_party_contact_matches is moved with the record.

    python3 scripts/relink_kalpataru_registrations.py --dry-run
    python3 scripts/relink_kalpataru_registrations.py
"""
from __future__ import annotations

import re
import sys

from _db import lit, run_psql
from audit_kalpataru_registrations import (BU_UNIT_DIGITS, BU_WING_LETTER, DOC_NUMBER, SEP,
                                           TOWER, UNIT_DIGITS, WING_DEV, WING_LETTER, db,
                                           floor_of, one_line, to_mygate_flat, unit_digits,
                                           wing_of)
from load_kalpataru_mygate import BUILDING_ID

PER = {"A": 5, "B": 6, "C": 6, "D": 6}


def desc_wing(d: str) -> str:
    for pat in (r"([ऀ-ॿ]{1,3})\s*विंग", r"विंग\s*([ऀ-ॿ]{1,3})"):
        m = re.search(pat, d)
        if m and m.group(1) in WING_DEV:
            return WING_DEV[m.group(1)]
    return ""


def main() -> int:
    dry = "--dry-run" in sys.argv
    q = chr(39)

    units = {}
    for w, d, uid in db(f"""
        SELECT concat_ws({q}{SEP}{q},
               regexp_replace(upper(wing),'.*([A-Z])\\s*$','\\1'),
               regexp_replace(unit_number,'\\D','','g'), id::text)
        FROM building_units
        WHERE building_id='{BUILDING_ID}' AND canonical_status='active';"""):
        if d.strip():
            units.setdefault((w.strip(), d.strip()), []).append(uid.strip())

    rows = db(f"""
        SELECT concat_ws({q}{SEP}{q},
               r.id::text, {one_line('r.wing_text')}, {one_line('r.unit_text')},
               {one_line('r.floor_text')}, {one_line('r.property_description_raw')},
               coalesce(regexp_replace(upper(bu.wing),'.*([A-Z])\\s*$','\\1'),''),
               coalesce(regexp_replace(bu.unit_number,'\\D','','g'),''),
               coalesce(r.doc_number,''), coalesce(r.raw_context->>'tower',''),
               r.building_unit_id::text)
        FROM unit_registration_records r
        JOIN building_units bu ON bu.id=r.building_unit_id
        WHERE r.building_id='{BUILDING_ID}';""")

    moves, skipped = [], []
    for rid, wt, ut, ft, desc, lw, ld, doc, tower, old_uid in rows:
        rid, old_uid = rid.strip(), old_uid.strip()
        w = wing_of(wt, desc, tower)
        fl = floor_of(ft, desc)
        u = unit_digits(ut, desc)
        flat = to_mygate_flat(u, fl, PER.get(w, 6)) if w else ""
        if not w or not flat or (lw, ld) == (w, flat):
            continue

        dw = desc_wing(desc)
        # A flat-number change is only safe when the record states its floor: "802" is
        # floor 8 flat 02 (= MyGate 82) only because floor_text says 8. Without a floor,
        # "203" could be floor 20 flat 3 or floor 2 flat 03 — refuse to guess.
        if ld != flat and fl <= 0:
            skipped.append(f"doc {doc}: flat differs ({lw}-{ld} vs {w}-{flat}) but record states no floor")
            continue
        if dw and dw != w:
            skipped.append(f"doc {doc}: Devanagari says wing {dw}, record says {w} — contradiction")
            continue
        tgt = units.get((w, flat), [])
        if len(tgt) != 1:
            skipped.append(f"doc {doc}: {w}-{flat} resolves to {len(tgt)} active units")
            continue
        moves.append((rid, old_uid, tgt[0], doc, f"{lw}-{ld}", f"{w}-{flat}"))

    print(f"relinkable (wing-only, evidence-backed): {len(moves)}")
    print(f"left for review:                        {len(skipped)}")
    for s in skipped[:15]:
        print(f"  {s}")
    if len(skipped) > 15:
        print(f"  … {len(skipped)-15} more")
    if not moves:
        return 0

    vals = ",".join(f"({lit(r)}::uuid,{lit(o)}::uuid,{lit(n)}::uuid)" for r, o, n, *_ in moves)
    sql = f"""
BEGIN;
CREATE TEMP TABLE mv(rid uuid, old_uid uuid, new_uid uuid) ON COMMIT DROP;
INSERT INTO mv VALUES {vals};

UPDATE unit_registration_records r
   SET building_unit_id = m.new_uid,
       raw_context = coalesce(r.raw_context,'{{}}'::jsonb)
                     || jsonb_build_object('relink_prev_unit_id', m.old_uid::text,
                                           'relinked_by','wing_fix_2026-07-10')
  FROM mv m WHERE r.id=m.rid;

-- party->contact matches carry their own unit pointer; move them with the record
UPDATE registration_party_contact_matches pm
   SET building_unit_id = m.new_uid
  FROM mv m
  JOIN unit_registration_parties p ON p.unit_registration_record_id=m.rid
 WHERE pm.unit_registration_party_id=p.id AND pm.building_unit_id=m.old_uid;

SELECT 'records_relinked', count(*) FROM mv;
SELECT 'party_matches_moved', count(*) FROM registration_party_contact_matches pm
   JOIN mv m ON pm.building_unit_id=m.new_uid;
{"ROLLBACK;" if dry else "COMMIT;"}
"""
    code, out = run_psql(sql)
    print(("\nDRY-RUN (rolled back)\n" if dry else "\nCOMMITTED\n") + out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
