#!/usr/bin/env python3
"""QA every linked registration against its Index II source capture.

For each registration linked to an apartment, find the Index II text snapshot for its
(doc_number, registration_year) under exports/, parse the register's own
"(4) Property Description" line, and confirm three things independently of the DB:

    Building Name   e.g. "Kalpataru Radiance, A - Tower - ORA" / "Imperial HeightsTower C CHSL"
    Wing            from the flat prefix ("B-3205", "A/1103") or a TOWER/Tower token
    Flat number     "Apartment/Flat No:..." + "Floor No:..."

Flat numbering differs per building and the two must never be conflated:

    Kalpataru Radiance   flat = floor*10  + position   (floor 29 flat 1  = 291)
    Imperial Heights     flat = floor*100 + position   (floor 11 flat 3  = 1103)

The register also writes some Kalpataru flats in the floor*100 form ("2703" = floor 27,
flat 3 = 273), so the floor is used to normalise before comparing.

Records with no snapshot fall back to property_description_raw, which is the same register
text as stored at ingest — reported separately as weaker evidence, never silently merged.

Building-name rule (operator, 2026-07-10): only records whose source explicitly names
Kalpataru Radiance belong to Kalpataru Radiance. Anything naming another project (the
register calls some of these "द मिडोस" / The Meadows) is reported as foreign, not deleted.

    python3 scripts/qa_registration_sources.py            # summary + samples
    python3 scripts/qa_registration_sources.py --all      # every finding
    python3 scripts/qa_registration_sources.py --csv out.csv
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from _db import lit, run_psql
from audit_kalpataru_registrations import DOC_NUMBER, SEP, db, to_mygate_flat
from parse_igr_xls_exports import load as load_xls, tcells

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "exports"
# Snapshots MUST be scoped per building: IGR doc numbers restart each year per SRO office, so
# doc 8188/2024 exists in both capture sets as two different flats in two different buildings.
SNAP_DIRS = {
    "Kalpataru Radiance": ROOT / "igr_index2_snapshots",
    "Imperial Heights": ROOT / "igr_index2_snapshots_imperial_heights",
}
# IGR "SearchResult*.xls" are UTF-16 HTML search-result pages — the sheets the doc numbers
# were harvested from. They carry the same Property Description, so they are a fallback
# source for records whose Index II was never captured.
XLS_DIRS = [REPO / "imports" / "igr Registrations", Path.home() / "Downloads"]

# building name -> (expected name fragment, flat scheme, units per floor)
BUILDINGS = {
    "Kalpataru Radiance": ("kalpataru radiance", "floor10", {"A": 5, "B": 6, "C": 6, "D": 6}),
    "Imperial Heights": ("imperial heights", "floor100", {}),
}

FILE_RE = re.compile(r"capture_\d+_doc(\d+)_(\d{4})_r\d+\.txt$")
# The register runs fields together with no comma ("A/204Shop No:Floor No:12.00Building Name:"),
# so stop at the next field label as well as at a comma. Without this the flat token swallows
# the floor and the building name, and every digit run gets concatenated.
STOP = r"(?=,|\s*Shop\s*No|\s*Floor\s*No|\s*Building\s*Name|\s*Block\s*Sector|\s*Address\s*:|$)"
FLAT_RE = re.compile(r"Apartment/Flat\s*No\s*:\s*(.*?)" + STOP, re.I)
FLOOR_RE = re.compile(r"Floor\s*No\s*:\s*(\d+)", re.I)
BNAME_RE = re.compile(r"Building\s*Name\s*:\s*(.*?)"
                      r"(?=,\s*Block\s*Sector|\s*Block\s*Sector|\s*Address\s*:|,\s*Road\s*:|$)",
                      re.I | re.S)
DEV_FLAT = re.compile(r"सदनिका\s*नं[:\s]*([0-9]+)")
DEV_FLOOR = re.compile(r"माळा\s*नं[:\s]*([0-9]+)")
DEV_WING = re.compile(r"([ऀ-ॿ]{1,3})\s*विंग|विंग\s*([ऀ-ॿ]{1,3})")
WING_DEV = {"ए": "A", "बी": "B", "सी": "C", "डी": "D"}
DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# Projects the register is known to name around these plots. A source naming ANY of these
# other than the record's own building, IN THE PROPERTY DESCRIPTION'S Building Name field, is
# a cross-project mislink.
#
# Two traps that must not be confused with that:
#   * a document may be registered at ANY SRO office, so the SRO never identifies the
#     building. It is used only as part of a document's identity (doc number + year + SRO).
#   * "कल्पतरू सिनर्जी" (Kalpataru Synergy) shows up in party_address — it is the developer's
#     registered office ("Office no. 101, Kalpataru Synergy"), not the property. Party
#     addresses are never read as evidence of which building a flat is in.
PROJECTS = {
    "kalpataru radiance": (r"kalpataru\s*rad|kalpataru\s*radinace|कल्पतरू\s*रेडीयंस", "Kalpataru Radiance"),
    "kalpataru synergy": (r"kalpataru\s*synergy|सिनर्जी", "Kalpataru Synergy"),
    "kalpataru residency": (r"kalpataru\s*residency", "Kalpataru Residency"),
    "the meadows": (r"\bmeadow|मिडोस", "The Meadows"),
    "imperial heights": (r"imperial\s*heights|इम्पेरिअल", "Imperial Heights"),
    "ekta tripolis": (r"ekta|tripolis|ट्रायपॉलीस", "Ekta Tripolis"),
    "oberoi esquire": (r"oberoi|esquire", "Oberoi Esquire"),
    "windsor grande": (r"windsor", "Windsor Grande"),
}


def projects_named(text: str) -> set[str]:
    low = (text or "").lower()
    return {label for pat, label in PROJECTS.values() if re.search(pat, low, re.I)}


def wing_from(flat_raw: str, bname: str) -> str:
    """Wing letter from the flat token ("B-3205", "A/1103") or a tower token in the name."""
    m = re.match(r"\s*([A-D])\s*[-/]", flat_raw or "")
    if m:
        return m.group(1).upper()
    for text in (flat_raw or "", bname or ""):
        m = re.search(r"TOWER\s*[-:]?\s*([A-D])\b", text, re.I)
        if m:
            return m.group(1).upper()
        m = re.search(r"\b([A-D])\s*[-–]\s*TOWER\b", text, re.I)
        if m:
            return m.group(1).upper()
    return ""


ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
            "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "ground": 0}
FLOOR_WORD_RE = re.compile(r"Floor\s*No\s*:\s*([A-Za-z]+)", re.I)


def parse_index2(text: str) -> dict | None:
    # Scope to the property-description clause. Index II files carry other "Floor"/number text
    # (area, party addresses); searching the whole file picks up the wrong floor.
    seg = re.search(r"Apartment/Flat\s*No.{0,400}", text, re.I | re.S)
    text = seg.group(0) if seg else text
    fm, flm, bm = FLAT_RE.search(text), FLOOR_RE.search(text), BNAME_RE.search(text)
    if not fm:
        return None
    if not flm:                                    # "Floor No:SECOND FLOOR"
        wm = FLOOR_WORD_RE.search(text)
        if wm and wm.group(1).lower() in ORDINALS:
            flm = type("M", (), {"group": lambda self, i, v=ORDINALS[wm.group(1).lower()]: str(v)})()
    flat_raw = fm.group(1).strip()
    bname = " ".join((bm.group(1) if bm else "").split())
    # "D-4309/4409" is one duplex spanning two floors; the lower flat is the anchor.
    digits = re.sub(r"\D", "", flat_raw.split("/")[0] if "/" in flat_raw
                    and re.search(r"\d/\d", flat_raw) else flat_raw)
    return {"flat_raw": flat_raw, "digits": digits,
            "floor": int(flm.group(1)) if flm else -1,
            "bname": bname, "wing": wing_from(flat_raw, bname)}


def parse_devanagari(text: str) -> dict | None:
    f, fl = DEV_FLAT.search(text), DEV_FLOOR.search(text)
    if not f:
        return None
    w = ""
    m = DEV_WING.search(text)
    if m:
        w = WING_DEV.get(m.group(1) or m.group(2), "")
    bm = re.search(r"इमारतीचे\s*नाव[:\s]*([^,]{1,40})", text)
    return {"flat_raw": f.group(1), "digits": f.group(1),
            "floor": int(fl.group(1)) if fl else -1,
            "bname": (bm.group(1).strip() if bm else ""), "wing": w}


def norm_sro(s: str) -> str:
    return re.sub(r"[^0-9a-zऀ-ॿ]", "", (s or "").lower())


def load_snapshots() -> dict[tuple[str, str, str], dict]:
    """(building, doc, year) -> Index II property description."""
    snaps: dict[tuple[str, str, str], dict] = {}
    for building, d in SNAP_DIRS.items():
        if not d.exists():
            continue
        for p in d.rglob("capture_*_doc*_r*.txt"):
            m = FILE_RE.search(p.name)
            if not m:
                continue
            key = (building, m.group(1), m.group(2))
            if key in snaps:                       # keep the first capture per doc/year
                continue
            got = parse_index2(p.read_text(encoding="utf-8", errors="replace"))
            if got:
                got["file"] = str(p.relative_to(ROOT.parent))
                snaps[key] = got
    return snaps


def load_searchresults() -> dict[tuple[str, str, str], dict]:
    """(doc_number, year, sro) -> parsed property description, from the IGR SearchResult*.xls sheets.

    Keyed on (doc, year, SRO). Doc numbers restart each year AND repeat across SRO offices, so
    a doc-number-only key silently matches another project's registration — doc 11112 in one
    year is a Kalpataru flat, in another an Ekta Tripolis flat. Ambiguous keys are dropped
    rather than guessed, and a sheet never overrides an Index II capture.

    SRO is part of a document's IDENTITY only. Any document may be registered at any SRO
    office, so the office never tells you which building the property is in.
    """
    seen: dict[tuple[str, str, str], dict] = {}
    dupes: set[tuple[str, str, str]] = set()
    for d in XLS_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.rglob("SearchResult*.xls")):
            try:
                html_text = load_xls(p)
            except Exception:
                continue
            hdr, idx = None, {}
            for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html_text, re.S | re.I):
                cells = tcells(row)
                if not cells:
                    continue
                low = [c.strip().lower() for c in cells]
                if hdr is None and "docno" in low and "propertydescription" in low:
                    hdr = low
                    idx = {name: i for i, name in enumerate(low)}
                    continue
                if hdr is None or len(cells) <= idx.get("propertydescription", 99):
                    continue
                doc = cells[idx["docno"]].strip()
                date = cells[idx["registrationdate"]].strip() if "registrationdate" in idx else ""
                sro = cells[idx["sroname"]].strip() if "sroname" in idx else ""
                ym = re.search(r"(\d{4})", date)
                if not doc or not ym or not sro:
                    continue
                key = (doc, ym.group(1), norm_sro(sro))
                got = parse_index2(cells[idx["propertydescription"]]) or \
                    parse_devanagari(cells[idx["propertydescription"]])
                if not got:
                    continue
                got["file"] = str(p)
                if key in seen and seen[key]["flat_raw"] != got["flat_raw"]:
                    dupes.add(key)                 # same doc+year, different flat: unusable
                seen.setdefault(key, got)
    for k in dupes:
        seen.pop(k, None)
    if dupes:
        print(f"SearchResult: dropped {len(dupes)} ambiguous (doc, year) keys")
    return seen


def expected_flat(scheme: str, digits: str, floor: int, per: int) -> str:
    """Flat number as the DB stores it for this building, from the register's own token.

    The register writes the flat three ways: full number ("2601"), the other scheme's full
    number (Kalpataru "2703" for flat 273), or bare position with the floor alongside
    ("A-03, Floor No:17th" = Imperial Heights 1703). The floor disambiguates all three.
    """
    if not digits:
        return ""
    n = int(digits)
    if scheme == "floor100":                       # Imperial Heights: floor*100 + position
        if floor > 0:
            if 1 <= n <= 12:
                return str(floor * 100 + n)        # position only
            if n // 100 == floor:
                return digits                      # already full
            return ""
        return digits if len(digits) >= 3 else ""
    # Kalpataru Radiance: floor*10 + position
    if floor > 0 and 1 <= n <= per:
        return str(floor * 10 + n)                 # position only
    return to_mygate_flat(digits, floor, per)


def enqueue(rows: list[tuple[str, str, str]], dry: bool) -> None:
    """Put every non-confirmed record on the human review queue, once.

    Idempotent on (unit_registration_record_id, review_type): re-running the QA after new
    Index II captures land must not pile up duplicate cards.
    """
    if not rows:
        print("nothing to enqueue")
        return
    vals = ",".join(f"({lit(rid)}::uuid,{lit(rtype)},{lit(detail)})" for rid, rtype, detail in rows)
    sql = f"""
BEGIN;
CREATE TEMP TABLE q(rid uuid, rtype text, detail text) ON COMMIT DROP;
INSERT INTO q VALUES {vals};

INSERT INTO unit_registration_review_items
       (building_id, unit_registration_record_id, review_type, status, priority,
        decision_notes, raw_context)
SELECT r.building_id, r.id, q.rtype, 'pending',
       CASE WHEN q.rtype='source_qa_conflict' THEN 'high' ELSE 'normal' END,
       q.detail,
       jsonb_build_object('source','qa_registration_sources',
                          'phase','source_doc_qa_2026_07_10',
                          'is_fake', false, 'external_calls_made', false)
FROM q JOIN unit_registration_records r ON r.id=q.rid
WHERE NOT EXISTS (SELECT 1 FROM unit_registration_review_items i
                   WHERE i.unit_registration_record_id=r.id AND i.review_type=q.rtype);

SELECT 'queued_total', count(*) FROM unit_registration_review_items
  WHERE raw_context->>'source'='qa_registration_sources';
SELECT review_type, count(*) FROM unit_registration_review_items
  WHERE raw_context->>'source'='qa_registration_sources' GROUP BY 1 ORDER BY 1;
{"ROLLBACK;" if dry else "COMMIT;"}
"""
    code, out = run_psql(sql)
    print(("\nDRY-RUN queue (rolled back)\n" if dry else "\nQUEUE COMMITTED\n") + out)


def main() -> int:
    show_all = "--all" in sys.argv
    csv_path = None
    if "--csv" in sys.argv:
        csv_path = sys.argv[sys.argv.index("--csv") + 1]

    snaps = load_snapshots()
    sheets = load_searchresults()
    print(f"Index II snapshots parsed: {len(snaps)}")
    print(f"SearchResult sheet rows:   {len(sheets)}\n")

    rows = db(f"""
        SELECT concat_ws(chr(31), r.id::text, b.name, {DOC_NUMBER},
               coalesce(r.registration_year::text,''),
               coalesce(regexp_replace(upper(bu.wing),'.*([A-Z])\\s*$','\\1'),'?'),
               coalesce(regexp_replace(bu.unit_number,'\\D','','g'),'?'),
               translate(coalesce(r.property_description_raw,''), chr(10)||chr(13)||chr(9)||chr(31), '    '),
               coalesce(nullif(r.sro_office,''),'-'))
        FROM unit_registration_records r
        JOIN buildings b ON b.id=r.building_id
        JOIN building_units bu ON bu.id=r.building_unit_id
        WHERE b.name IN ('Kalpataru Radiance','Imperial Heights');""")

    stats: dict[str, Counter] = defaultdict(Counter)
    findings: dict[str, list] = defaultdict(list)
    out_rows: list[list] = []
    queue_rows: list[tuple[str, str, str, str]] = []

    for rid, bname_db, doc, year, lw, ld, desc, sro in rows:
        want_name, scheme, per_map = BUILDINGS[bname_db]
        # Evidence tiers, strongest first. Index II is the register's own extract; the
        # SearchResult sheet is the search page it was harvested from; the stored
        # description is the same text as captured at ingest.
        src, evidence = snaps.get((bname_db, doc, year)), "index2"
        if not src:
            src, evidence = sheets.get((doc, year, norm_sro(sro))), "searchresult"
        if not src:
            src = parse_index2(desc) or parse_devanagari(desc)
            evidence = "db_description" if src else "none"
        if not src:
            stats[bname_db]["no evidence"] += 1
            findings[bname_db].append(f"[needs_review] doc {doc}/{year} linked {lw}-{ld}: "
                                      f"no source document found")
            queue_rows.append((rid, "source_qa_no_document", "no Index II, SearchResult row or description found"))
            continue

        per = per_map.get(src["wing"] or lw, 6)
        exp = expected_flat(scheme, src["digits"], src["floor"], per)

        low = (src["bname"] or "").lower()
        name_ok = want_name in low
        wing_ok = (not src["wing"]) or src["wing"] == lw
        flat_ok = bool(exp) and exp == ld

        # A source that names a DIFFERENT project is a data problem; one that names only a
        # wing ("ORA") or nothing is merely unproven. Keep them apart — per the operator,
        # only an explicit "Kalpataru Radiance" confirms the building.
        conflicts, unproven = [], []
        if src["wing"] and not wing_ok:
            conflicts.append(f"wing {src['wing']} vs linked {lw}")
        if exp and not flat_ok:
            conflicts.append(f"flat {exp} vs linked {ld}")
        named = projects_named(src["bname"])
        foreign = named - {bname_db}
        if foreign and not name_ok:
            conflicts.append(f"names another project: {', '.join(sorted(foreign))} ({src['bname']!r})")
        if not exp:
            unproven.append(f"flat unresolved from {src['flat_raw']!r} (floor {src['floor']})")
        if not name_ok:
            unproven.append(f"building not named ({src['bname'] or 'absent'!r})")
        if evidence != "index2" and DEVANAGARI.search(src["bname"] or "") :
            unproven.append("Devanagari source text")

        if conflicts:
            verdict, detail = "CONFLICT", "; ".join(conflicts + unproven)
        elif unproven:
            verdict, detail = "needs_review", "; ".join(unproven)
        else:
            verdict, detail = "confirmed", "OK"

        stats[bname_db][f"{verdict} ({evidence})"] += 1
        if verdict != "confirmed":
            findings[bname_db].append(
                f"[{verdict}] doc {doc}/{year} linked {lw}-{ld} ({evidence}): {detail}")
            queue_rows.append((rid,
                               "source_qa_conflict" if verdict == "CONFLICT" else "source_qa_needs_review",
                               f"{evidence}: {detail}"[:900]))
        out_rows.append([bname_db, doc, year, lw, ld, evidence, src["bname"],
                         src["flat_raw"], src["floor"], src["wing"], exp, verdict, detail])

    for b in BUILDINGS:
        print(f"=== {b} ===")
        tot = sum(stats[b].values())
        for k, v in sorted(stats[b].items()):
            print(f"  {k:<28} {v:>5}   ({v*100//max(tot,1)}%)")
        print(f"  {'total linked':<28} {tot:>5}")
        f = findings[b]
        if f:
            print(f"  findings ({len(f)}):")
            for x in (f if show_all else f[:12]):
                print(f"    {x}")
            if not show_all and len(f) > 12:
                print(f"    … {len(f)-12} more (--all)")
        print()

    if "--enqueue" in sys.argv:
        enqueue(queue_rows, dry="--dry-run" in sys.argv)

    if csv_path:
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["building", "doc", "year", "linked_wing", "linked_flat", "evidence",
                        "source_building_name", "source_flat", "source_floor", "source_wing",
                        "expected_flat", "verdict", "detail"])
            w.writerows(out_rows)
        print(f"wrote {len(out_rows)} rows to {csv_path}")

    return 0 if not any(findings.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
