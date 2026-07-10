#!/usr/bin/env python3
"""Attach registrations that have no building_unit to the right apartment.

Same evidence ladder as qa_registration_sources.py — the register decides, never the DB:

    1. Index II text capture   exports/igr_index2_snapshots{,_imperial_heights}/…_docN_YYYY_r0.txt
    2. SearchResult sheet      imports/igr Registrations/**/SearchResult*.xls, ~/Downloads
    3. property_description_raw as stored at ingest

A record is linked only when ALL of these hold:

  * wing and flat both resolve;
  * if the flat number needs normalising between the two schemes (Kalpataru floor*10+position
    vs Imperial Heights floor*100+position, and the register writes Kalpataru flats both ways),
    the record states an explicit floor — bare "203" is floor 20 flat 3 OR floor 2 flat 03;
  * the source's Building Name, when it names a project at all, names THIS building;
  * exactly one active building_unit matches (wing, flat).

Anything else is left unlinked and queued for a human on the existing review kanban
(unit_registration_review_items → vw_unit_registration_review_queue), with the reason.
Deeds over land / development rights / OC name no apartment and are skipped silently — they
are correctly unlinked, not a gap.

    python3 scripts/link_unlinked_registrations.py --dry-run
    python3 scripts/link_unlinked_registrations.py
    python3 scripts/link_unlinked_registrations.py --enqueue     # queue the leftovers too
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict

from _db import lit, run_psql
from audit_kalpataru_registrations import SEP, db, nz, one_line
from qa_registration_sources import (BUILDINGS, DEVANAGARI, expected_flat, load_searchresults,
                                     load_snapshots, norm_sro, parse_devanagari, parse_index2,
                                     projects_named)

Q = chr(39)


def main() -> int:
    dry = "--dry-run" in sys.argv
    do_queue = "--enqueue" in sys.argv

    snaps = load_snapshots()
    sheets = load_searchresults()
    print(f"Index II snapshots {len(snaps)}   SearchResult rows {len(sheets)}\n")

    # active units per building, keyed (building, wing, flat)
    units: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for bname, w, d, uid in db(f"""
        SELECT concat_ws({Q}{SEP}{Q}, b.name,
               {nz("regexp_replace(upper(bu.wing),'.*([A-Z])" + chr(92) + "s*$','" + chr(92) + "1')")},
               {nz("regexp_replace(bu.unit_number,'" + chr(92) + "D','','g')")}, bu.id::text)
        FROM building_units bu JOIN buildings b ON b.id=bu.building_id
        WHERE bu.canonical_status='active'
          AND b.name IN ('Kalpataru Radiance','Imperial Heights');"""):
        if d.strip():
            units[(bname, w.strip(), d.strip())].append(uid.strip())

    rows = db(f"""
        SELECT concat_ws({Q}{SEP}{Q}, r.id::text, b.name,
               {nz("coalesce(r.doc_number,'')")},
               {nz("coalesce(r.registration_year::text,'')")},
               {one_line('r.property_description_raw')},
               {nz("coalesce(r.sro_office,'')")})
        FROM unit_registration_records r
        JOIN buildings b ON b.id=r.building_id
        WHERE r.building_unit_id IS NULL
          AND b.name IN ('Kalpataru Radiance','Imperial Heights');""")

    links, queue = [], []
    stats: Counter = Counter()

    for rid, bname, doc, year, desc, sro in rows:
        want_name, scheme, per_map = BUILDINGS[bname]
        src, evidence = snaps.get((bname, doc, year)), "index2"
        if not src:
            src, evidence = sheets.get((doc, year, norm_sro(sro))), "searchresult"
        if not src:
            src = parse_index2(desc) or parse_devanagari(desc)
            evidence = "db_description" if src else "none"

        if not src or not src.get("digits"):
            stats["no flat named (land / OC / development rights)"] += 1
            continue

        wing = src["wing"]
        per = per_map.get(wing, 6)
        flat = expected_flat(scheme, src["digits"], src["floor"], per)

        reason = None
        if not wing:
            reason = f"wing not resolved (flat {src['flat_raw']!r})"
        elif not flat:
            reason = f"flat not resolved from {src['flat_raw']!r} (floor {src['floor']})"
        else:
            foreign = projects_named(src["bname"]) - {bname}
            if foreign and want_name not in (src["bname"] or "").lower():
                reason = f"source names another project: {', '.join(sorted(foreign))}"
            else:
                tgt = units.get((bname, wing, flat), [])
                if len(tgt) != 1:
                    reason = f"{wing}-{flat} matches {len(tgt)} active units"

        if reason:
            stats[f"needs review ({evidence})"] += 1
            queue.append((rid, "source_qa_needs_review", f"unlinked: {evidence}: {reason}"[:900]))
            continue

        # Devanagari-only evidence still links when wing+flat are unambiguous, but say so.
        dev = DEVANAGARI.search(src["bname"] or "") or DEVANAGARI.search(src["flat_raw"] or "")
        stats[f"LINK ({evidence})"] += 1
        links.append((rid, units[(bname, wing, flat)][0], evidence, f"{wing}-{flat}", bool(dev)))

    print("outcome:")
    for k, v in sorted(stats.items()):
        print(f"  {k:<44} {v:>4}")
    print(f"\n  linkable {len(links)}   queued for review {len(queue)}")
    for rid, uid, ev, flat, dev in links[:10]:
        print(f"    link -> {flat:<8} via {ev}{'  [devanagari]' if dev else ''}")
    if len(links) > 10:
        print(f"    … {len(links)-10} more")

    if links:
        vals = ",".join(f"({lit(r)}::uuid,{lit(u)}::uuid,{lit(e)},{lit(f)})" for r, u, e, f, _ in links)
        sql = f"""
BEGIN;
CREATE TEMP TABLE lk(rid uuid, uid uuid, ev text, flat text) ON COMMIT DROP;
INSERT INTO lk VALUES {vals};

UPDATE unit_registration_records r
   SET building_unit_id = lk.uid,
       raw_context = coalesce(r.raw_context,'{{}}'::jsonb)
                     || jsonb_build_object('linked_by','source_evidence_2026-07-10',
                                           'link_evidence', lk.ev, 'link_flat', lk.flat)
  FROM lk WHERE r.id=lk.rid AND r.building_unit_id IS NULL;

SELECT 'linked_now', count(*) FROM lk;
SELECT b.name, count(*) FROM unit_registration_records r JOIN buildings b ON b.id=r.building_id
 WHERE r.building_unit_id IS NULL AND b.name IN ('Kalpataru Radiance','Imperial Heights')
 GROUP BY 1 ORDER BY 1;
{"ROLLBACK;" if dry else "COMMIT;"}
"""
        code, out = run_psql(sql)
        print(("\nDRY-RUN (rolled back)\n" if dry else "\nCOMMITTED\n") + out)

    if do_queue and queue:
        vals = ",".join(f"({lit(r)}::uuid,{lit(t)},{lit(d)})" for r, t, d in queue)
        sql = f"""
BEGIN;
CREATE TEMP TABLE q(rid uuid, rtype text, detail text) ON COMMIT DROP;
INSERT INTO q VALUES {vals};
INSERT INTO unit_registration_review_items
       (building_id, unit_registration_record_id, review_type, status, priority,
        decision_notes, raw_context)
SELECT r.building_id, r.id, q.rtype, 'pending', 'normal', q.detail,
       jsonb_build_object('source','link_unlinked_registrations',
                          'phase','unlinked_link_2026_07_10',
                          'is_fake', false, 'external_calls_made', false)
FROM q JOIN unit_registration_records r ON r.id=q.rid
WHERE NOT EXISTS (SELECT 1 FROM unit_registration_review_items i
                   WHERE i.unit_registration_record_id=r.id AND i.review_type=q.rtype);
SELECT 'queued', count(*) FROM q;
{"ROLLBACK;" if dry else "COMMIT;"}
"""
        code, out = run_psql(sql)
        print(("\nDRY-RUN queue (rolled back)\n" if dry else "\nQUEUE COMMITTED\n") + out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
