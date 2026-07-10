#!/usr/bin/env python3
"""Audit that every Kalpataru registration is linked to the right apartment.

Two flat-numbering schemes collide in this building:

  MyGate / most IGR rows   flat = floor*10  + position   ("273" = floor 27, flat 3)
  some IGR Index-II rows   flat = floor*100 + position   ("2703" = floor 27, flat 3)

Both describe the SAME apartment. A record carrying "2703" must link to the unit
MyGate calls "273". Verified: of the 4-digit unit_texts that also carry a floor,
158/158 satisfy floor*100+position with position in 1..6, and none satisfy
floor*10+position. So the scheme is decidable, not guessed.

For every Kalpataru registration this recovers (wing, flat) from the record's own
wing_text / unit_text / floor_text and the Devanagari property_description_raw,
normalises it to the MyGate scheme, and compares it against the building_unit the
record is actually linked to. Where the record cannot be resolved on its own, it
cross-checks the registration's party names against MyGate's residents of the
candidate flat — the tie-break the operator would do by hand.

Verdicts:
  ok         linked unit == recovered flat
  mislinked  linked unit != recovered flat  (the record is on the wrong apartment)
  unlinked   no building_unit, but the flat was recovered  (linkable)
  unclear    wing and/or flat could not be recovered       (needs a human)

    python3 scripts/audit_kalpataru_registrations.py
    python3 scripts/audit_kalpataru_registrations.py --all
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict

from _db import run_psql
from load_kalpataru_mygate import BUILDING_ID, load_residents, norm_name

WING_DEV = {"ए": "A", "बी": "B", "सी": "C", "डी": "D"}
SEP = "\x1f"
NUL = "\x02"  # placeholder for an empty field; see one_line()


def db(sql: str) -> list[list[str]]:
    code, out = run_psql(sql)
    if code != 0:
        sys.exit(f"psql failed:\n{out}")
    # split("\n"), NOT splitlines(): psql ends rows with \n, but splitlines() also breaks on
    # \v, \f, U+2028 and friends, which occur inside the Devanagari descriptions.
    return [[("" if f == NUL else f) for f in ln.split(SEP)]
            for ln in out.strip("\n").split("\n") if ln.strip()]


def one_line(col: str) -> str:
    """Make a column safe to pack into one concat_ws row.

    Two traps, both hit for real on this table:
      * a newline inside the Devanagari description splits the psql row. translate() on
        literal control chars — not a regex escape, since '\\n' in a standard SQL literal
        is a backslash and an n and does not reach the regex engine.
      * concat_ws collapses EMPTY string arguments, not just NULLs, so a record with a
        null wing_text comes back with fewer fields than it has columns. Substitute a
        placeholder that db() maps back to ''.
    """
    q = chr(39)
    ctrl = f"chr(10)||chr(13)||chr(9)||chr({ord(SEP)})"
    return nz(f"translate(coalesce({col},''), {ctrl}, {q}    {q})")


def nz(expr: str) -> str:
    """Any column packed into concat_ws must go through this — empty args are collapsed."""
    q = chr(39)
    return f"coalesce(nullif({expr}, {q}{q}), chr({ord(NUL)}))"


# Backslashes cannot appear inside f-string expressions, so build these once, up front.
BS = chr(92)
WING_LETTER = nz(f"regexp_replace(upper(coalesce(bu.wing,'')),'.*([A-Z]){BS}s*$','{BS}1')")
UNIT_DIGITS = nz(f"regexp_replace(coalesce(bu.unit_number,''),'{BS}D','','g')")
BU_WING_LETTER = nz(f"regexp_replace(upper(wing),'.*([A-Z]){BS}s*$','{BS}1')")
BU_UNIT_DIGITS = nz(f"regexp_replace(unit_number,'{BS}D','','g')")
DOC_NUMBER = nz("coalesce(r.doc_number,'')")
LINK_EVIDENCE = nz("coalesce(r.raw_context->>'link_evidence','')")
TOWER = nz("coalesce(r.raw_context->>'tower','')")
PARTY_NAME = nz("replace(coalesce(nullif(p.party_name_english,''), p.party_name_raw, ''), chr(31), ' ')")
BU_FILTER_WING = f"regexp_replace(upper(bu.wing),'.*([A-Z]){BS}s*$','{BS}1')"
BU_FILTER_UNIT = f"regexp_replace(bu.unit_number,'{BS}D','','g')"
MK_FILTER_WING = f"regexp_replace(upper(m.wing),'.*([A-Z]){BS}s*$','{BS}1')"


def wing_of(wing_text: str, desc: str, tower: str = "") -> str:
    """Wing letter. raw_context.tower is what the IGR sheet itself recorded — most reliable."""
    if tower and tower.strip().upper() in "ABCD" and len(tower.strip()) == 1:
        return tower.strip().upper()
    m = re.search(r"\b([A-D])\b", (wing_text or "").upper())
    if m:
        return m.group(1)
    m = re.search(r"([ऀ-ॿ]{1,3})\s*विंग", desc or "")
    if m and m.group(1) in WING_DEV:
        return WING_DEV[m.group(1)]
    m = re.search(r"विंग\s*([ऀ-ॿ]{1,3})", desc or "")
    if m and m.group(1) in WING_DEV:
        return WING_DEV[m.group(1)]
    m = re.search(r"\b([A-D])[\s-]?WING|WING[\s-]?([A-D])\b", (desc or "").upper())
    return (m.group(1) or m.group(2)) if m else ""


def floor_of(floor_text: str, desc: str) -> int:
    d = re.sub(r"\D", "", floor_text or "")
    if d:
        return int(d)
    m = re.search(r"माळा\s*नं[:\s]*([0-9]+)", desc or "")
    return int(m.group(1)) if m else -1


def unit_digits(unit_text: str, desc: str) -> str:
    d = re.sub(r"\D", "", unit_text or "")
    if d:
        return d
    m = re.search(r"सदनिका\s*नं[:\s]*([0-9]+)", desc or "")
    return m.group(1) if m else ""


def to_mygate_flat(u: str, fl: int, per_floor: int) -> str:
    """Normalise a register flat number to MyGate's floor*10+position scheme."""
    if not u:
        return ""
    n = int(u)
    if fl > 0:
        for base in (100, 10):                    # floor*100+pos first: "2703" -> 27,3
            pos = n - fl * base
            if 1 <= pos <= per_floor:
                return str(fl * 10 + pos)
        return ""                                  # floor known but nothing fits: unclear
    # No floor on the record: infer from length. 4 digits is always floor*100+pos.
    if len(u) == 4:
        f, pos = n // 100, n % 100
        return str(f * 10 + pos) if 1 <= pos <= per_floor else ""
    return u                                       # already the MyGate scheme


def main() -> int:
    show_all = "--all" in sys.argv
    PER = {"A": 5, "B": 6, "C": 6, "D": 6}

    residents = load_residents()
    mygate_flats = {(r["wing"], r["flatd"]) for r in residents}
    mygate_names: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in residents:
        mygate_names[(r["wing"], r["flatd"])].add(norm_name(r["name"]))

    # Devanagari descriptions contain '|' and newlines: join on an ASCII unit separator and
    # flatten embedded newlines, or psql's line-per-row output splits a single record in two.
    q = chr(39)
    rows = db(f"""
        SELECT concat_ws({q}{SEP}{q},
               r.id::text, {one_line('r.wing_text')}, {one_line('r.unit_text')},
               {one_line('r.floor_text')},
               {one_line('r.property_description_raw')},
               {WING_LETTER}, {UNIT_DIGITS}, {DOC_NUMBER}, {TOWER}, {LINK_EVIDENCE})
        FROM unit_registration_records r
        LEFT JOIN building_units bu ON bu.id=r.building_unit_id
        WHERE r.building_id='{BUILDING_ID}';""")

    # party names per record, for the name cross-check
    parties: dict[str, set[str]] = defaultdict(set)
    for rid, nm in db(f"""
        SELECT concat_ws({q}{SEP}{q}, p.unit_registration_record_id::text,
               {PARTY_NAME})
        FROM unit_registration_parties p
        JOIN unit_registration_records r ON r.id=p.unit_registration_record_id
        WHERE r.building_id='{BUILDING_ID}';"""):
        parties[rid.strip()].add(norm_name(nm))

    verdict = Counter()
    mislinked, unclear, unlinked_ok, not_in_mygate = [], [], [], []
    name_confirms = name_contradicts = 0

    for rid, wt, ut, ft, desc, lw, ld, doc, tower, link_ev in rows:
        rid = rid.strip()
        w = wing_of(wt, desc, tower)
        fl = floor_of(ft, desc)
        u = unit_digits(ut, desc)
        flat = to_mygate_flat(u, fl, PER.get(w, 6)) if w else ""

        if not w or not flat:
            # A deed over land, development rights or an OC names no flat at all. It is
            # correctly unlinked, not a gap — only count it as unclear if it has a flat
            # number we failed to resolve, or is linked to a unit despite naming no flat.
            if not u and not ld:
                verdict["no_flat"] += 1
                continue
            # Placed from Zapkey's index (date + transaction type), not from its own text:
            # the deed names the land, so there is nothing here to reconcile against.
            if link_ev.startswith("zapkey"):
                verdict["zapkey_placed"] += 1
                continue
            verdict["unclear"] += 1
            unclear.append(f"doc {doc or '—'}  wing={w or '?'} unit_text={ut or '—'!r} floor={ft or '—'} "
                           f"linked={lw + '-' + ld if ld else 'none'}")
            continue

        if (w, flat) not in mygate_flats:
            not_in_mygate.append(f"doc {doc or '—'}  {w}-{flat} (recovered) not a MyGate flat; linked={lw+'-'+ld if ld else 'none'}")

        if not ld:
            verdict["unlinked"] += 1
            unlinked_ok.append(f"doc {doc or '—'}  -> {w}-{flat}")
            continue

        if (lw, ld) == (w, flat):
            verdict["ok"] += 1
            continue

        verdict["mislinked"] += 1
        # cross-check party names against MyGate residents of each candidate flat
        pn = parties.get(rid, set())
        hit_rec = bool(pn & mygate_names.get((w, flat), set()))
        hit_link = bool(pn & mygate_names.get((lw, ld), set()))
        tag = ""
        if hit_rec and not hit_link:
            tag = "  [party name matches RECOVERED flat]"; name_confirms += 1
        elif hit_link and not hit_rec:
            tag = "  [party name matches LINKED flat]"; name_contradicts += 1
        mislinked.append(f"doc {doc or '—'}  linked {lw}-{ld}  but record says {w}-{flat}{tag}")

    # Buildings must never share a unit. Kalpataru numbers flats floor*10+position and
    # Imperial Heights floor*100+position, so a stray link across buildings would place a
    # flat on a plausible-looking but wrong floor rather than failing loudly.
    cross = db("""
        SELECT concat_ws(chr(31), rec_building, unit_building, n::text) FROM (
          SELECT rb.name rec_building, ub.name unit_building, count(*) n
          FROM unit_registration_records r
          JOIN buildings rb ON rb.id=r.building_id
          JOIN building_units bu ON bu.id=r.building_unit_id
          JOIN buildings ub ON ub.id=bu.building_id
          WHERE bu.building_id <> r.building_id
          GROUP BY 1,2) t;""")
    if cross:
        print("CROSS-BUILDING LINKS (must be zero):")
        for rb, ub, n in cross:
            print(f"  {n} registrations of {rb} linked to units of {ub}")
    else:
        print("cross-building links: none ✓")

    total = sum(verdict.values())
    print("Kalpataru Radiance — registration ↔ apartment audit")
    print(f"  registrations        {total}")
    for k in ("ok", "mislinked", "unlinked", "unclear", "no_flat", "zapkey_placed"):
        print(f"  {k:<20} {verdict[k]}")
    print("  (no_flat = deeds over land / development rights / OC that name no apartment)")
    print("  (zapkey_placed = deed names no flat; placed via Zapkey date+type, on the confirm kanban)")
    if verdict["mislinked"]:
        print(f"\n  of the mislinked: party names back the RECOVERED flat in {name_confirms}, "
              f"the LINKED flat in {name_contradicts}, inconclusive in "
              f"{verdict['mislinked']-name_confirms-name_contradicts}")

    for label, rows_ in (("MISLINKED", mislinked), ("RECOVERED FLAT NOT IN MYGATE", not_in_mygate),
                         ("UNLINKED BUT RESOLVABLE", unlinked_ok), ("UNCLEAR", unclear)):
        if rows_:
            print(f"\n{label} ({len(rows_)}):")
            for x in (rows_ if show_all else rows_[:12]):
                print(f"  {x}")
            if not show_all and len(rows_) > 12:
                print(f"  … {len(rows_)-12} more (--all)")

    return 0 if not (mislinked or unclear or cross) else 1


if __name__ == "__main__":
    raise SystemExit(main())
