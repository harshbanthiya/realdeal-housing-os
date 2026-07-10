#!/usr/bin/env python3
"""Link flat-less registrations to an apartment using Zapkey's index as the join key.

206 of the still-unlinked Kalpataru registrations are mortgage deeds whose property
description names the LAND, not a flat — so no amount of text parsing will place them.
Zapkey indexes the same registrations WITH a flat, so (registration_date, transaction_type)
joins the two.

This is weaker evidence than an Index II, and it is treated that way:

  * a record is linked only when that (date, type) maps to exactly ONE Zapkey flat AND
    exactly ONE of our unlinked records — otherwise it is ambiguous and left alone;
  * where Zapkey shows several flats that day, the registration's party names are checked
    against the contacts already on each candidate flat, and a single hit breaks the tie.
    (In practice this rescues almost nothing here: the parties on these deeds are the
    developer and the lender, not residents.);
  * every link records raw_context.link_evidence='zapkey_date_type' and
    link_confidence='medium', and files a `zapkey_link_confirm` card on the review kanban
    so a human confirms it. The link is reversible: building_unit_id was NULL before.

    python3 scripts/link_by_zapkey.py --dry-run
    python3 scripts/link_by_zapkey.py
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict

from _db import lit, run_psql
from load_kalpataru_mygate import BUILDING_ID, norm_name

# our transaction_category -> Zapkey transaction_type
CATEGORY = {"encumbrance": "mortgage", "ownership": "sale", "tenancy": "rent"}


def rows(sql: str) -> list[list[str]]:
    code, out = run_psql(sql)
    if code != 0:
        sys.exit(out)
    return [ln.split("|") for ln in out.strip().splitlines() if ln.strip()]


def main() -> int:
    dry = "--dry-run" in sys.argv

    ours: dict[tuple[str, str], list[str]] = defaultdict(list)
    for rid, d, cat in rows(f"""
        SELECT id::text, coalesce(registration_date::text,''), coalesce(transaction_category,'')
        FROM unit_registration_records
        WHERE building_unit_id IS NULL AND building_id='{BUILDING_ID}';"""):
        t = CATEGORY.get(cat.strip())
        if d.strip() and t:
            ours[(d.strip(), t)].append(rid.strip())

    zap: dict[tuple[str, str], set[str]] = defaultdict(set)
    for d, t, uid in rows("""
        SELECT coalesce(registration_date::text,''), transaction_type, building_unit_id::text
        FROM zapkey_transactions WHERE building_unit_id IS NOT NULL;"""):
        if d.strip():
            zap[(d.strip(), t.strip())].add(uid.strip())

    parties: dict[str, set[str]] = defaultdict(set)
    for rid, nm in rows(f"""
        SELECT p.unit_registration_record_id::text,
               coalesce(nullif(p.party_name_english,''), p.party_name_raw, '')
        FROM unit_registration_parties p
        JOIN unit_registration_records r ON r.id=p.unit_registration_record_id
        WHERE r.building_unit_id IS NULL AND r.building_id='{BUILDING_ID}';"""):
        parties[rid.strip()].add(norm_name(nm))

    unit_names: dict[str, set[str]] = defaultdict(set)
    for uid, nm in rows(f"""
        SELECT r.building_unit_id::text, c.full_name
        FROM contact_property_relationships r
        JOIN contacts c ON c.id=r.contact_id
        JOIN building_units bu ON bu.id=r.building_unit_id
        WHERE bu.building_id='{BUILDING_ID}';"""):
        unit_names[uid.strip()].add(norm_name(nm))

    links: list[tuple[str, str, str]] = []
    stats: Counter = Counter()
    for key, recs in ours.items():
        flats = zap.get(key, set())
        if not flats:
            stats["no Zapkey row for that date+type"] += len(recs)
            continue
        if len(flats) == 1 and len(recs) == 1:
            links.append((recs[0], next(iter(flats)), "zapkey_date_type"))
            stats["LINK — unique flat, unique record"] += 1
            continue
        if len(flats) > 1:
            for rid in recs:
                pn = parties.get(rid, set())
                hit = [u for u in flats if pn & unit_names.get(u, set())]
                if len(hit) == 1:
                    links.append((rid, hit[0], "zapkey_date_type+party_name"))
                    stats["LINK — party name broke the tie"] += 1
                else:
                    stats["ambiguous: Zapkey shows several flats that day"] += 1
            continue
        stats["ambiguous: several of our records that day+type"] += len(recs)

    print("outcome:")
    for k, v in sorted(stats.items()):
        print(f"  {k:<52} {v:>4}")
    print(f"\n  linkable {len(links)}")
    if not links:
        return 0

    vals = ",".join(f"({lit(r)}::uuid,{lit(u)}::uuid,{lit(e)})" for r, u, e in links)
    sql = f"""
BEGIN;
CREATE TEMP TABLE lk(rid uuid, uid uuid, ev text) ON COMMIT DROP;
INSERT INTO lk VALUES {vals};

UPDATE unit_registration_records r
   SET building_unit_id = lk.uid,
       raw_context = coalesce(r.raw_context,'{{}}'::jsonb)
                     || jsonb_build_object('linked_by','zapkey_join_2026-07-10',
                                           'link_evidence', lk.ev,
                                           'link_confidence','medium')
  FROM lk WHERE r.id=lk.rid AND r.building_unit_id IS NULL;

-- weaker evidence than an Index II: every one of these wants a human eye
INSERT INTO unit_registration_review_items
       (building_id, unit_registration_record_id, review_type, status, priority,
        decision_notes, raw_context)
SELECT r.building_id, r.id, 'zapkey_link_confirm', 'pending', 'normal',
       'linked to ' || bu.wing || ' ' || bu.unit_number ||
       ' from Zapkey (date + transaction type). Deed names no flat — confirm before treating as canonical.',
       jsonb_build_object('source','link_by_zapkey','phase','zapkey_join_2026_07_10',
                          'is_fake', false, 'external_calls_made', false)
FROM lk JOIN unit_registration_records r ON r.id=lk.rid
        JOIN building_units bu ON bu.id=lk.uid
WHERE NOT EXISTS (SELECT 1 FROM unit_registration_review_items i
                   WHERE i.unit_registration_record_id=r.id AND i.review_type='zapkey_link_confirm');

SELECT 'linked', count(*) FROM lk;
SELECT 'kalpataru_still_unlinked', count(*) FROM unit_registration_records
   WHERE building_unit_id IS NULL AND building_id='{BUILDING_ID}';
{"ROLLBACK;" if dry else "COMMIT;"}
"""
    code, out = run_psql(sql)
    print(("\nDRY-RUN (rolled back)\n" if dry else "\nCOMMITTED\n") + out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
