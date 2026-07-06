#!/usr/bin/env python3
"""Independent QA audit of Imperial Heights + Kalpataru Radiance unit registrations.

Deliberately does NOT import parse_igr_index2_pdfs.py / ingest_igr_bulk_snapshots.py /
parse_igr_xls_exports.py or any other production ingest/parse script. All extraction
logic here is written fresh so a bug shared by the production parsers can't hide from
this check (2026-07-06: production pipeline mis-filed 6 Imperial Heights records and
89 Kalpataru records under the wrong building -- this script exists so that doesn't
happen silently again).

Pipeline:
  1. Walk every raw Index II .txt capture under both snapshot roots, and every raw
     .xls results-grid export under exports/igr_raw_xls_archive/.
  2. Independently extract doc_no / year / sro / building-name-guess / wing / flat / floor
     from the RAW TEXT of each file (keyword search, not the production regex tables).
  3. Read the DB (read-only) for every unit_registration_records row in both buildings.
  4. Match DB row <-> raw file by (doc_no, year, normalized SRO). Classify:
       CONFIRMED       - raw doc found, building-name-guess agrees with DB's building
       MISMATCH        - raw doc found, building-name-guess names a DIFFERENT building
       UNCLEAR         - raw doc found, but no building keyword detected in raw text
       NO_RAW_FOUND    - no raw capture/xls-row for this doc at all
  5. Walk every building_units row (apartment) and roll up the attached records' status
     into an apartment-by-apartment report: confirmed / needs_attention / no_data.
  6. Write JSON + Markdown reports under exports/qa_independent_audit/.

Usage:
    python scripts/qa_independent_audit.py            # run the full audit
    python scripts/qa_independent_audit.py --selftest  # run self_check() only, no DB/disk scan
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from _db import run_psql  # noqa: E402  (read-only queries only in this file)

OUT_DIR = PROJECT_ROOT / "exports" / "qa_independent_audit"

SNAPSHOT_ROOTS = [
    PROJECT_ROOT / "exports" / "igr_index2_snapshots",
    PROJECT_ROOT / "exports" / "igr_index2_snapshots_imperial_heights",
]
XLS_ARCHIVE = PROJECT_ROOT / "exports" / "igr_raw_xls_archive"

BUILDINGS = {
    "imperial_heights": {
        "db_name": "Imperial Heights",
        "building_id_sql": "'0e72db71-8b93-4ecd-879c-17d8d8f2b206'",
        # "epitome residency" confirmed 2026-07-06 as IH's actual promoter entity (named
        # respondent in 25+ MahaRERA complaints for IH Wing C/D, alongside "WADHWA/RADIUS/
        # EPITOME RESIDENCY PVT LTD") -- every raw doc mentioning it also already carries an
        # explicit "Imperial Heights" building-name match, so this is a defensive backstop,
        # not currently load-bearing.
        "keywords": [r"imperial\s*heights", r"इम्पीरियल", r"इंपीरियल", r"इम्पेरियल", r"इम्पेरिअल",
                     r"इम्पिरियल", r"epitome\s*residency"],
    },
    "kalpataru_radiance": {
        "db_name": "Kalpataru Radiance",
        "building_id_sql": "(SELECT id FROM buildings WHERE name ILIKE '%kalpataru%radiance%' LIMIT 1)",
        # NOTE: deliberately no bare "कल्पतर" pattern -- the builder has other unrelated
        # projects (e.g. "कल्पतरू इस्टेट" / Kalpataru Estate, 2745 hits in our own raw
        # corpus) that would falsely match on the root alone. Every pattern here requires
        # the "radiance"/रेडियंस-family root specifically, found by exhaustively enumerating
        # every real spelling variant in our own captures 2026-07-06 (qa_independent_audit
        # self-audit): rेडीयंस (1028), रेडियन्स (79), रेडियंस (69), रेडिअन्स (55), रेडीयन्स (13).
        "keywords": [r"kalpataru?\w*\s*radi[ae]nce", r"रेडियंस", r"रेडीयंस", r"रेिडयंस",
                     r"रेडियन्स", r"रेडिअन्स", r"रेडीयन्स",
                     r"ora,?\s*kalpataru", r"brill?ance kalpataru"],
    },
}
# Buildings we know share the same SRO jurisdiction and have shown up as contamination.
# Not tracked in our DB -- detecting them just proves a DB record is misfiled.
KNOWN_OTHER_BUILDINGS = [
    (r"patra\s*ch[ae]wl", "patra_chawl"),
    (r"siddharth\s*nagar\s*chs", "patra_chawl"),
    (r"पत्रा\s*चाळ", "patra_chawl"),
    (r"roma\s*tower|lodha\s*fiorenza", "roma_tower_lodha_fiorenza"),
    (r"dattani\s*shelter", "dattani_shelter"),
    (r"kamla\s*gulmohar\s*heights", "kamla_gulmohar_heights"),
    (r"dheeraj\s*residency", "dheeraj_residency"),
]

WING_LETTER_RE = re.compile(
    r"(?:wing|tower)\s*[-–\s]*([ABCDabcd])\b"
    r"|\b([ABCDabcd])\s*[-–\s]*(?:wing|tower)\b"
    r"|(?:विंग|टॉवर)\s*(ए|बी|सी|डी)|(ए|बी|सी|डी)\s*[-–\s]*(?:विंग|टॉवर)",
    re.I,
)
_DEVA_WING = {"ए": "A", "बी": "B", "सी": "C", "डी": "D"}

FLAT_RE = re.compile(
    r"(?:Apartment/Flat No|Flat No|फ्लॅट\s*(?:नं|क्र)?\.?|सदनिका\s*(?:नं|क्रमांक|क्र)?\.?)\s*[:.]?\s*"
    r"([0-9A-Za-z][0-9A-Za-z/\-]*)",
    re.I,
)
FLOOR_RE = re.compile(
    r"(?:Floor No|मजला|माळा\s*(?:नं\.?|क्रमांक|क्र\.?)?)\s*[:.]?\s*([0-9A-Za-z]+)"
    r"|([0-9]+)\s*(?:वा|व्या|था|ला)?\s*मजल",
    re.I,
)
DOC_NO_EN_RE = re.compile(r"Doc\s*No\.?\s*:\s*(\d+)\s*/\s*(\d{4})", re.I)
DOC_NO_MR_RE = re.compile(r"दस्त\s*क्रमांक\s*[:：]?\s*([0-9]+)\s*/\s*([0-9]{4})")
SRO_EN_RE = re.compile(r"Sro\s*Name\s*:\s*(.+)", re.I)
SRO_MR_RE = re.compile(r"दुय्यम\s*निबंधक\s*[:：]?\s*(.+)")

_DEVA_CITY = {"मुंबई": "mumbai", "बोरिवली": "borivali", "बोरीवली": "borivali", "ठाणे": "thane", "पुणे": "pune"}


def normalize_sro(raw: str | None) -> str | None:
    """Collapse 'Joint S.R. Mumbai 25' / 'सह दु.नि.मुंबई 25' / 'सह दु.नि. मुंबई-25' to 'mumbai_25'."""
    if not raw:
        return None
    s = raw.strip()
    for deva, en in _DEVA_CITY.items():
        s = s.replace(deva, en)
    s = s.lower()
    m_num = re.search(r"(\d+)\s*$", s)
    if not m_num:
        return None
    num = m_num.group(1)
    m_loc = re.search(r"(mumbai|borivali|thane|pune)", s)
    loc = m_loc.group(1) if m_loc else "unk"
    return f"{loc}_{num}"


def guess_building(text: str) -> tuple[str | None, str | None]:
    """Return (canonical_key, matched_snippet) for the first recognised building keyword.

    canonical_key is one of BUILDINGS' keys, one of KNOWN_OTHER_BUILDINGS' labels, or None
    if no keyword matched at all (UNCLEAR).
    """
    for key, cfg in BUILDINGS.items():
        for pat in cfg["keywords"]:
            m = re.search(pat, text, re.I)
            if m:
                return key, m.group(0)
    for pat, label in KNOWN_OTHER_BUILDINGS:
        m = re.search(pat, text, re.I)
        if m:
            return label, m.group(0)
    return None, None


def guess_wing(text: str) -> str | None:
    m = WING_LETTER_RE.search(text)
    if m:
        g = next((g for g in m.groups() if g), None)
        if g:
            return _DEVA_WING.get(g, g.upper())
    # Fallback: flat number prefixed with a wing letter, e.g. "A-2202" or "A/153"
    fm = re.search(r"(?:Flat No|फ्लॅट)\D{0,10}?\b([ABCDabcd])[\-/]\d", text, re.I)
    return fm.group(1).upper() if fm else None


def guess_flat(text: str) -> str | None:
    m = FLAT_RE.search(text)
    return m.group(1).strip() if m else None


def guess_floor(text: str) -> str | None:
    m = FLOOR_RE.search(text)
    if not m:
        return None
    return (m.group(1) or m.group(2) or "").strip() or None


def extract_property_field(text: str) -> str:
    """Return ONLY the '(4) Property Description' field, not the whole document.

    Party name/address fields ((7)/(8), or Marathi field 7 seller / field 8 purchaser)
    routinely contain their OWN 'Building Name:' / 'इमारतीचे नाव' text -- a party's home
    address, unrelated to the flat being registered. Searching the whole document for
    building keywords means a buyer who happens to live in "Imperial Heights" makes a
    genuine Kalpataru Radiance document look contaminated. Confirmed 2026-07-06 on docs
    12618/2024 and 6793/2022 -- both explicitly say Kalpataru Radiance / CTS 260/5A in
    the property field, but a party's address elsewhere in the doc says Imperial Heights.
    """
    m = re.search(r"\(4\)[^\n]*\n?(.*?)\(5\)", text, re.S)
    if m:
        return m.group(1)
    # English free-search format sometimes labels it "Property Description" without the
    # leading "(4)" landing in the same line as expected; fall back to age-marker cutoff
    # (party blocks always carry an age near the name; the property field never does).
    cut = re.split(r"\bAge:\s*\d+|वय:-\s*\d+", text)[0]
    return cut


def parse_index2_txt(path: Path) -> dict | None:
    """Independent extraction from one raw Index II .txt capture."""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = DOC_NO_EN_RE.search(text) or DOC_NO_MR_RE.search(text)
    if not m:
        return None
    doc_no, year = m.group(1), m.group(2)
    sro_m = SRO_EN_RE.search(text) or SRO_MR_RE.search(text)
    sro_raw = sro_m.group(1).strip()[:120] if sro_m else None
    prop_field = extract_property_field(text)
    building_key, snippet = guess_building(prop_field)
    return {
        "raw_file": str(path.relative_to(PROJECT_ROOT)),
        "raw_kind": "index2_txt",
        "doc_no": doc_no,
        "year": year,
        "sro_raw": sro_raw,
        "sro_norm": normalize_sro(sro_raw),
        "building_guess": building_key,
        "building_guess_snippet": snippet,
        "wing_guess": guess_wing(prop_field),
        "flat_guess": guess_flat(prop_field),
        "floor_guess": guess_floor(prop_field),
    }


def discover_index2_files() -> list[Path]:
    files: list[Path] = []
    for root in SNAPSHOT_ROOTS:
        if root.exists():
            files.extend(sorted(root.glob("*_bulk/capture_*_r*.txt")))
    return files


def parse_xls_file(path: Path) -> list[dict]:
    """Independent extraction from one raw .xls results-grid export (HTML table, UTF-16)."""
    try:
        tables = pd.read_html(path, encoding="utf-16")
    except Exception as e:  # noqa: BLE001
        print(f"  [xls] failed to parse {path.name}: {e}")
        return []
    if not tables:
        return []
    df = tables[0]
    df.columns = [str(c).strip().lower() for c in df.columns]
    out = []
    for _, row in df.iterrows():
        # Only the propertydescription column -- NOT sellerparty/purchaserparty, which
        # can themselves carry a party's own building/address text.
        prop_field = str(row.get("propertydescription", ""))
        docno_val = str(row.get("docno", ""))
        doc_m = re.search(r"^\s*(\d+)\s*/\s*(\d{4})", docno_val)
        if not doc_m:
            # DocNo column sometimes just the number, year comes from RegistrationDate/dateofexecution
            doc_m2 = re.match(r"^\s*(\d+)\s*$", docno_val)
            date_src = str(row.get("registrationdate", "")) or str(row.get("dateofexecution", ""))
            date_m = re.search(r"(\d{4})", date_src)
            if not (doc_m2 and date_m):
                continue
            doc_no, year = doc_m2.group(1), date_m.group(1)
        else:
            doc_no, year = doc_m.group(1), doc_m.group(2)
        sro_raw = str(row.get("sroname", "")).strip() or None
        building_key, snippet = guess_building(prop_field)
        out.append({
            "raw_file": str(path.relative_to(PROJECT_ROOT)),
            "raw_kind": "xls_results_grid",
            "doc_no": doc_no,
            "year": year,
            "sro_raw": sro_raw,
            "sro_norm": normalize_sro(sro_raw),
            "building_guess": building_key,
            "building_guess_snippet": snippet,
            "wing_guess": guess_wing(prop_field),
            "flat_guess": guess_flat(prop_field),
            "floor_guess": guess_floor(prop_field),
        })
    return out


def discover_xls_files() -> list[Path]:
    if not XLS_ARCHIVE.exists():
        return []
    return sorted(XLS_ARCHIVE.glob("*.xls"))


def build_raw_inventory() -> list[dict]:
    inventory: list[dict] = []
    txt_files = discover_index2_files()
    print(f"Found {len(txt_files)} raw Index II .txt captures")
    for i, p in enumerate(txt_files, 1):
        r = parse_index2_txt(p)
        if r:
            inventory.append(r)
        if i % 500 == 0:
            print(f"  ...{i}/{len(txt_files)} txt parsed")

    xls_files = discover_xls_files()
    print(f"Found {len(xls_files)} raw .xls results-grid exports")
    for p in xls_files:
        rows = parse_xls_file(p)
        inventory.extend(rows)
        print(f"  {p.name}: {len(rows)} rows")

    return inventory


def fetch_db_records() -> list[dict]:
    records = []
    for key, cfg in BUILDINGS.items():
        _, out = run_psql(f"""
            SELECT r.id, r.doc_number, r.registration_year, r.sro_office,
                   r.wing_text, r.unit_text, r.floor_text, r.building_unit_id,
                   COALESCE(r.property_description_raw,'') AS desc,
                   r.transaction_category
            FROM unit_registration_records r
            WHERE r.building_id = {cfg['building_id_sql']}
        """)
        for line in out.strip().splitlines():
            parts = line.split("|")
            if len(parts) < 9:
                continue
            rid, doc_no, year, sro, wing, unit, floor, bu_id, desc = parts[:9]
            cat = parts[9] if len(parts) > 9 else ""
            records.append({
                "building_key": key,
                "record_id": rid,
                "doc_no": doc_no,
                "year": year,
                "sro_raw": sro,
                "sro_norm": normalize_sro(sro),
                "wing_text": wing,
                "unit_text": unit,
                "floor_text": floor,
                "building_unit_id": bu_id or None,
                "has_description": bool(desc.strip()),
                "transaction_category": cat,
            })
    return records


def classify(db_rec: dict, raw_by_key: dict) -> dict:
    """doc_number is only unique within one (SRO, year) -- a same doc/year hit at a
    DIFFERENT SRO is a coincidental collision with an unrelated document, not evidence
    about this one. Only ever trust SRO-matching candidates (confirmed false-positive
    2026-07-06 on doc 9217/2019: a Mumbai-17 Kalpataru doc was wrongly used to judge a
    Mumbai-24 Imperial Heights doc of the same number)."""
    key = (db_rec["doc_no"], db_rec["year"])
    candidates = raw_by_key.get(key, [])
    pool = [c for c in candidates if db_rec["sro_norm"] and c["sro_norm"] == db_rec["sro_norm"]]
    if not pool:
        return {"status": "NO_RAW_FOUND", "raw_matches": []}
    guesses = {c["building_guess"] for c in pool if c["building_guess"]}
    if not guesses:
        return {"status": "UNCLEAR", "raw_matches": pool}
    if db_rec["building_key"] in guesses:
        status = "CONFIRMED" if guesses == {db_rec["building_key"]} else "MISMATCH"
    else:
        status = "MISMATCH"
    return {"status": status, "raw_matches": pool}


def audit() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Step 1/4: building raw document inventory ===")
    inventory = build_raw_inventory()
    with open(OUT_DIR / "raw_inventory.json", "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(inventory)} raw inventory rows -> raw_inventory.json")

    raw_by_key: dict[tuple, list[dict]] = defaultdict(list)
    for r in inventory:
        raw_by_key[(r["doc_no"], r["year"])].append(r)

    print("\n=== Step 2/4: fetching DB records ===")
    db_records = fetch_db_records()
    print(f"{len(db_records)} DB records across both buildings")

    print("\n=== Step 3/4: cross-checking ===")
    results = []
    status_counts: dict[str, int] = defaultdict(int)
    for rec in db_records:
        c = classify(rec, raw_by_key)
        rec = {**rec, **c}
        results.append(rec)
        status_counts[c["status"]] += 1
    print("Status counts:", dict(status_counts))

    mismatches = [r for r in results if r["status"] == "MISMATCH"]
    with open(OUT_DIR / "crosscheck_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Wrote crosscheck_results.json ({len(mismatches)} MISMATCH found)")

    print("\n=== Step 4/4: apartment-by-apartment rollup ===")
    for key, cfg in BUILDINGS.items():
        building_results = [r for r in results if r["building_key"] == key]
        _, units_out = run_psql(f"""
            SELECT id, wing, unit_number, floor FROM building_units
            WHERE building_id = {cfg['building_id_sql']}
            ORDER BY wing, unit_number
        """)
        units = []
        by_unit_id: dict[str, list[dict]] = defaultdict(list)
        for r in building_results:
            if r["building_unit_id"]:
                by_unit_id[r["building_unit_id"]].append(r)

        for line in units_out.strip().splitlines():
            parts = line.split("|")
            if len(parts) < 4:
                continue
            uid, wing, unit_no, floor = parts[:4]
            attached = by_unit_id.get(uid, [])
            if not attached:
                unit_status = "no_data"
            elif any(a["status"] == "CONFIRMED" for a in attached):
                unit_status = "confirmed"
            elif any(a["status"] == "MISMATCH" for a in attached):
                unit_status = "needs_attention_mismatch"
            else:
                unit_status = "needs_attention_unverified"
            units.append({
                "building_unit_id": uid, "wing": wing, "unit_number": unit_no, "floor": floor or None,
                "status": unit_status,
                "records": [{"doc_no": a["doc_no"], "year": a["year"], "status": a["status"]} for a in attached],
            })

        with open(OUT_DIR / f"apartments_{key}.json", "w", encoding="utf-8") as f:
            json.dump(units, f, ensure_ascii=False, indent=2)

        counts = defaultdict(int)
        for u in units:
            counts[u["status"]] += 1
        print(f"  {cfg['db_name']}: {len(units)} apartments -> {dict(counts)}")

        write_markdown_report(key, cfg, units, building_results)


def write_markdown_report(key: str, cfg: dict, units: list[dict], building_results: list[dict]) -> None:
    lines = [f"# Independent QA audit — {cfg['db_name']}", ""]
    counts = defaultdict(int)
    for u in units:
        counts[u["status"]] += 1
    lines.append("## Apartment rollup")
    for status, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"- **{status}**: {n}")
    lines.append("")

    mismatches = [r for r in building_results if r["status"] == "MISMATCH"]
    if mismatches:
        lines.append(f"## MISMATCH — {len(mismatches)} DB record(s) whose raw text names a different building")
        lines.append("| doc_no | year | sro | DB wing/unit | raw building guess | raw file |")
        lines.append("|---|---|---|---|---|---|")
        for r in mismatches:
            guesses = {c["building_guess"] for c in r["raw_matches"] if c["building_guess"]}
            files = ", ".join(c["raw_file"] for c in r["raw_matches"][:1])
            lines.append(
                f"| {r['doc_no']} | {r['year']} | {r['sro_raw']} | {r['wing_text']}/{r['unit_text']} "
                f"| {', '.join(guesses)} | {files} |"
            )
        lines.append("")

    unclear = [r for r in building_results if r["status"] == "UNCLEAR"]
    if unclear:
        lines.append(f"## UNCLEAR — {len(unclear)} record(s) with a raw file but no detectable building keyword")
        lines.append("| doc_no | year | sro | DB wing/unit | raw file |")
        lines.append("|---|---|---|---|---|")
        for r in unclear:
            files = ", ".join(c["raw_file"] for c in r["raw_matches"][:1])
            lines.append(f"| {r['doc_no']} | {r['year']} | {r['sro_raw']} | {r['wing_text']}/{r['unit_text']} | {files} |")
        lines.append("")

    no_raw = [r for r in building_results if r["status"] == "NO_RAW_FOUND"]
    lines.append(f"## NO_RAW_FOUND — {len(no_raw)} DB record(s) with no raw capture/xls-row to verify against")
    lines.append("(Expected for many `igr_xls_kalpataru`/bulk-ingest rows where only a DB-level "
                  "parse exists; re-capture via `fetch_igr_docno_targeted.py` to confirm any of these.)")
    lines.append("")

    no_data_units = [u for u in units if u["status"] == "no_data"]
    if no_data_units:
        lines.append(f"## Apartments with zero registration records ({len(no_data_units)})")
        sample = no_data_units[:40]
        lines.append(", ".join(f"{u['wing']}-{u['unit_number']}" for u in sample))
        if len(no_data_units) > len(sample):
            lines.append(f"... and {len(no_data_units) - len(sample)} more (see apartments_{key}.json)")
        lines.append("")

    with open(OUT_DIR / f"report_{key}.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  wrote report_{key}.md")


# ── search raw archive for apartments with zero DB records ────────────────────

def normalize_unit(u: str | None) -> str | None:
    """'A-93' / 'a/093' / '93,' / '093' all collapse to '93' for matching."""
    if not u:
        return None
    digits = re.sub(r"[^0-9A-Za-z]", "", u).upper()
    digits = digits.lstrip("ABCD")  # drop a leading wing-letter prefix like 'A93'
    return digits.lstrip("0") or digits or None


def filter_candidates_by_wing(candidates: list[dict], apartment_wing: str | None) -> list[dict]:
    """Keep ONLY candidates whose detected wing explicitly agrees with the apartment's
    wing. Unit numbers repeat across wings -- "501" exists separately in Wing A, B, and
    D -- so a candidate detected as a DIFFERENT wing is a different apartment, never a
    fallback match (confirmed 2026-07-06 on "B-501": fell back to A-501/D-501 docs,
    which the operator captured, correctly landing on A-501/D-501 and leaving B-501
    still empty).

    A candidate with NO detected wing at all is ALSO dropped, not kept as a maybe-match:
    confirmed 2026-07-06 on a second round -- all 4 "wingless" candidates queued for
    B-04/B-2102/C-05/B-2402 turned out (per the production parser's more thorough wing
    detection) to actually belong to Wing A/04, Wing D/2102, Wing B/1805, Wing A/2402
    respectively. My independent wing-guess regex failing to find a wing is evidence of
    nothing -- not evidence the doc belongs to THIS apartment.
    """
    if not apartment_wing or not candidates:
        return candidates
    wing_letter = re.sub(r"[^A-D]", "", apartment_wing.upper())[:1] or None
    return [c for c in candidates if c.get("wing_guess") == wing_letter]


def search_missing_units() -> None:
    """For every apartment with zero attached registration records, search the FULL
    raw document inventory (independent of doc_number/year -- we have none to look up)
    for any raw capture whose building-guess + wing + flat matches. Surfaces raw docs
    that exist on disk but were never ingested into the DB at all."""
    inv_path = OUT_DIR / "raw_inventory.json"
    if not inv_path.exists():
        print("raw_inventory.json not found -- run the full audit first (no args).")
        return
    inventory = json.load(open(inv_path, encoding="utf-8"))

    by_building_unit: dict[tuple, list[dict]] = defaultdict(list)
    for r in inventory:
        nu = normalize_unit(r.get("flat_guess"))
        if r.get("building_guess") and nu:
            by_building_unit[(r["building_guess"], nu)].append(r)

    for key, cfg in BUILDINGS.items():
        apt_path = OUT_DIR / f"apartments_{key}.json"
        if not apt_path.exists():
            print(f"apartments_{key}.json not found -- run the full audit first.")
            continue
        units = json.load(open(apt_path, encoding="utf-8"))
        no_data = [u for u in units if u["status"] == "no_data"]
        print(f"\n{cfg['db_name']}: searching raw archive for {len(no_data)} apartments with zero DB records")

        found, still_missing = [], []
        for u in no_data:
            nu = normalize_unit(u["unit_number"])
            candidates = by_building_unit.get((key, nu), []) if nu else []
            candidates = filter_candidates_by_wing(candidates, u.get("wing"))
            if candidates:
                found.append({**u, "raw_candidates": candidates})
            else:
                still_missing.append(u)

        print(f"  found in raw archive but never ingested: {len(found)}")
        print(f"  still no raw document at all: {len(still_missing)}")

        with open(OUT_DIR / f"missing_units_found_{key}.json", "w", encoding="utf-8") as f:
            json.dump(found, f, ensure_ascii=False, indent=2)
        with open(OUT_DIR / f"missing_units_notfound_{key}.json", "w", encoding="utf-8") as f:
            json.dump(still_missing, f, ensure_ascii=False, indent=2)

        lines = [f"# Missing-unit raw-archive search — {cfg['db_name']}", "",
                 f"{len(no_data)} apartments have zero attached registration records. "
                 f"Searched the full raw inventory ({len(inventory)} docs) by building + wing + flat number "
                 f"(independent of doc_number, since there's nothing in the DB to look up).", "",
                 f"- **Found in raw archive, never ingested**: {len(found)}",
                 f"- **No raw document at all** (genuinely never captured): {len(still_missing)}", ""]

        if found:
            lines.append("## Found in raw archive but missing from DB")
            lines.append("| wing | unit | candidate doc_no/year | sro | raw file |")
            lines.append("|---|---|---|---|---|")
            for u in found:
                for c in u["raw_candidates"][:3]:
                    lines.append(
                        f"| {u['wing']} | {u['unit_number']} | {c['doc_no']}/{c['year']} "
                        f"| {c['sro_raw']} | {c['raw_file']} |"
                    )
            lines.append("")

        if still_missing:
            lines.append(f"## No raw document found at all ({len(still_missing)})")
            lines.append("Never captured -- add to the docno-targeted queue or a fresh eSearch bulk crawl.")
            sample = still_missing[:60]
            lines.append(", ".join(f"{u['wing']}-{u['unit_number']}" for u in sample))
            if len(still_missing) > len(sample):
                lines.append(f"... and {len(still_missing) - len(sample)} more "
                              f"(see missing_units_notfound_{key}.json)")
            lines.append("")

        with open(OUT_DIR / f"missing_units_report_{key}.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  wrote missing_units_report_{key}.md")


# ── self-test ──────────────────────────────────────────────────────────────────

def self_check() -> None:
    """ponytail: smallest runnable check that fails if the independent parser breaks."""
    good_ih = ("Apartment/Flat No:A-2202, Floor No:22, Building Name:IMPERIAL HEIGHTS, "
               "Block Sector:GOREGAON WEST MUMBAI - 400104")
    good_kr = ("Apartment/Flat No:C-43, Floor No:4TH, Building Name:KALPATARU RADIANCE , "
               "Block Sector:GOREGAON WEST, MUMBAI")
    bad_roma = ("Apartment/Flat No:C-4504, Floor No:45, Building Name:Roma Tower, Lodha Fiorenza, "
                "Block Sector:Goregaon East, Mumbai")
    bad_dattani = "Apartment/Flat No:B-705, Floor No:7, Building Name:Dattani Shelter, Block Sector:Goregaon West"
    bad_patra = "सदनिका नं: फ्लॅट नं. 501, बिल्डींग नं. 1 सी, इमारतीचे नाव: पत्रा चाळ,सिद्धार्थ नगर सीएचएस लिमिटेड"

    assert guess_building(good_ih)[0] == "imperial_heights", "IH keyword detection broke"
    assert guess_building(good_kr)[0] == "kalpataru_radiance", "Kalpataru keyword detection broke"
    assert guess_building(bad_roma)[0] not in ("imperial_heights", "kalpataru_radiance"), \
        "Roma Tower should NOT match either tracked building"
    assert guess_building(bad_dattani)[0] not in ("imperial_heights", "kalpataru_radiance")
    assert guess_building(bad_patra)[0] == "patra_chawl"

    assert guess_wing(good_ih) == "A"
    assert guess_flat(good_ih) == "A-2202"
    assert guess_floor(good_ih) == "22"

    assert normalize_sro("Joint S.R. Mumbai 25") == "mumbai_25"
    assert normalize_sro("सह दु.नि.मुंबई 25") == "mumbai_25"
    assert normalize_sro("सह दु.नि. बोरीवली 4") == "borivali_4"

    m = DOC_NO_EN_RE.search("Doc No. : 23809/2023")
    assert m and m.group(1) == "23809" and m.group(2) == "2023"
    m2 = DOC_NO_MR_RE.search("दस्त क्रमांक : 15238 / 2025")
    assert m2 and m2.group(1) == "15238" and m2.group(2) == "2025"

    # Regression: doc 12618/2024 -- genuinely Kalpataru Radiance in field (4), but the
    # purchaser's home address in field (7)/(8) happens to be "Imperial Heights". A whole
    # -document keyword scan misclassified this as MISMATCH on 2026-07-06; the fix is to
    # restrict guess_building to extract_property_field()'s output only.
    doc_12618 = (
        "(4) भू-मापन,पोटहिस्सा व घरक्रमांक(असल्यास)\n"
        "1) पालिकेचे नाव:Mumbai Ma.na.pa. इतर वर्णन :सदनिका नं: ए-93, "
        "इमारतीचे नाव: ओरा,कल्पतरु रेडीयंस, ब्लॉक नं: गोरेगाव(पश्चिम),मुंबई - 400104\n"
        "(5) क्षेत्रफळ\t1450 चौ.फूट\n"
        "(7) दस्तऐवज करुन देणा-या\n"
        "1):  नाव:-सुरेंद्र पुजारी वय:-65 पत्ता:- ...\n"
        "सुकीर्ति काण्डपाल वय:-36; पत्ता:- इमारतीचे नाव: इंपीरियल हाइट्स सीएचएसएल\n"
    )
    prop_only = extract_property_field(doc_12618)
    assert "इंपीरियल" not in prop_only, "field(4) extraction leaked past the (5) marker"
    assert guess_building(prop_only)[0] == "kalpataru_radiance", \
        "party-address false positive regressed: doc 12618 should resolve to Kalpataru, not Imperial Heights"

    # Regression: doc numbers are unique only within (SRO, year) -- a raw candidate at a
    # DIFFERENT SRO must never be used to judge a DB record. False positive found
    # 2026-07-06 on doc 9217/2019 (DB record at Mumbai-24, unrelated raw doc at Mumbai-17).
    db_rec = {"doc_no": "9217", "year": "2019", "sro_norm": "mumbai_24", "building_key": "imperial_heights"}
    raw_by_key = {("9217", "2019"): [{"sro_norm": "mumbai_17", "building_guess": "kalpataru_radiance",
                                       "raw_file": "x", "wing_guess": None, "flat_guess": None, "floor_guess": None}]}
    result = classify(db_rec, raw_by_key)
    assert result["status"] == "NO_RAW_FOUND", \
        f"cross-SRO doc-number collision must be NO_RAW_FOUND, got {result['status']}"

    assert normalize_unit("A-93") == "93"
    assert normalize_unit("093") == "93"
    assert normalize_unit("93,") == "93"
    assert normalize_unit("B/306") == "306"

    # Regression: unit "501" exists separately in Wing A, B, and D. Searching for
    # apartment B-501 must never fall back to A-501/D-501 candidates just because no
    # Wing-B candidate exists -- that's a different apartment, not a weaker match.
    candidates_501 = [
        {"wing_guess": "A", "doc_no": "9029"},
        {"wing_guess": "D", "doc_no": "9632"},
    ]
    assert filter_candidates_by_wing(candidates_501, "B") == [], \
        "must not fall back to a different wing's candidates"
    assert filter_candidates_by_wing(candidates_501, "A") == [candidates_501[0]]
    # A candidate with NO detected wing is dropped too, not kept as a maybe-match --
    # confirmed 2026-07-06 round 2: all 4 "wingless" candidates queued this way turned
    # out to belong to a different apartment once ingested for real.
    wingless = [{"wing_guess": None, "doc_no": "123"}]
    assert filter_candidates_by_wing(wingless, "B") == []

    print("self_check: all assertions passed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--search-missing", action="store_true",
                     help="search raw archive for apartments with zero DB records (needs a prior full audit run)")
    args = ap.parse_args()
    self_check()
    if args.search_missing:
        search_missing_units()
    elif not args.selftest:
        audit()
