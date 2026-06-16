#!/usr/bin/env python3
"""Phase 6.19 — review-gated parser: IGR eSearch RESULTS-LIST snapshots -> staging records/parties.

Reads the captured IGR results-grid HTML pages (capture_*.html with table id=RegistrationGrid) from
ONE snapshot folder, dedupes rows across pages, normalizes the (Marathi/English) document type into
our category (ownership/tenancy/encumbrance/other), parses the property description for
building/wing/flat/floor/area (+ rent/tenure/deposit for leave-and-license), parses the seller/
purchaser name arrays, and transliterates Devanagari names to Latin (offline). It writes review-gated
rows ONLY for the TARGET building (Wing A-Ora = "Kalpataru Radiance A"); other wings / Patra Chawl on
the same CTS are summarised in counts but NOT written.

Dry-run by default. Writing requires --apply AND --real-ok. Reversible via --revert.

This is the LIST-level (Level 1) parser: it gets parties + type + which-flat + when. It does NOT add
price — consideration/market value/stamp duty live on the Index II detail (a later targeted pass).
Records are verification_status='parsed_candidate' (NOT verified); no canonical merge; party names
are PUBLIC-register PII kept raw + transliterated. NO scrape/IGR/external call (reads local snapshot).

Requires: pip install indic-transliteration  (offline at runtime).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import unicodedata
from html import unescape
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "6.19"
SOURCE = "igr_parse_kalpataru_2026"
RERA_REG = "P51800000591"

# Document type normalization: raw (lowercased substring) -> (english_type, category).
DOCTYPE_RULES = [
    ("लिव्ह", "leave_and_license", "tenancy"),
    ("लायसन", "leave_and_license", "tenancy"),
    ("leave and licen", "leave_and_license", "tenancy"),
    ("बक्षीस", "gift_deed", "ownership"),
    ("gift", "gift_deed", "ownership"),
    ("सेल डीड", "sale_deed", "ownership"),
    ("खरेदीखत", "sale_deed", "ownership"),
    ("विक्रीपत्र", "sale_deed", "ownership"),
    ("sale", "sale_deed", "ownership"),
    ("करारनामा", "agreement_to_sell", "ownership"),
    ("agreement for sale", "agreement_to_sell", "ownership"),
    ("agreement to sale", "agreement_to_sell", "ownership"),
    ("deposit of title deeds", "mortgage", "encumbrance"),
    ("pawn", "mortgage", "encumbrance"),
    ("गहाण", "mortgage", "encumbrance"),
    ("mortgage", "mortgage", "encumbrance"),
    ("conveyance", "conveyance", "ownership"),
    ("अभिहस्तांतरण", "conveyance", "ownership"),
]

# Roles by category for (seller-column, purchaser-column).
ROLE_BY_CATEGORY = {
    "ownership": ("seller", "purchaser"),
    "tenancy": ("lessor", "lessee"),
    "encumbrance": ("mortgagee", "mortgagor"),
    "other": ("seller", "purchaser"),
}

# Wing detection -> canonical label; TARGET is Wing A-Ora.
WING_RULES = [
    (("ora", "ओरा", "ऑरा"), "Wing A-Ora"),
    (("allura", "allure", "अल्लुरा", "अल्ल्युरा", "ॲलुरा", "अलुरा"), "Wing C-Allura"),
    (("lumina", "lumIna", "लुमिना", "लुमीना"), "Wing D-Lumina"),
    (("brilliance", "brilliance", "ब्रिलियन्स", "ब्रिल्लीयन्स", "ब्रिलीयन्स"), "Wing B-Brilliance"),
    (("patra", "पत्रा चाळ", "पत्रा"), "Patra Chawl (MHADA rehab)"),
]
TARGET_WING = "Wing A-Ora"


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with ENV_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    command = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql", "-U", user, "-d", db_name,
        "-v", "ON_ERROR_STOP=1", "-At", "-F", "|",
    ]
    result = subprocess.run(command, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip() or result.stderr.strip()


# ---- transliteration (offline) ----
try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate as _translit
    _HAVE_TRANSLIT = True
except Exception:  # noqa: BLE001
    _HAVE_TRANSLIT = False

DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def ascii_fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def translit_name(raw: str) -> str:
    """Latin transliteration of a (possibly Devanagari) name, ASCII-folded & lowercased for matching."""
    if not raw:
        return ""
    if DEVANAGARI.search(raw) and _HAVE_TRANSLIT:
        try:
            out = _translit(raw, sanscript.DEVANAGARI, sanscript.IAST)
        except Exception:  # noqa: BLE001
            out = raw
    else:
        out = raw
    return re.sub(r"\s+", " ", ascii_fold(out)).strip().lower()


# ---- HTML grid parsing ----
def parse_grid(html_text: str) -> list[list[str]]:
    m = re.search(r'id="RegistrationGrid".*?</table>', html_text, re.S)
    if not m:
        return []
    seg = m.group(0)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", seg, re.S)
    out = []
    for r in rows:
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)
        if len(cells) < 9:
            continue
        clean = [unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in cells]
        if clean[0] == "DocNo" or not re.match(r"^\d+$", clean[0]):
            continue  # header / non-data row
        out.append(clean)
    return out


def parse_name_array(cell: str) -> list[str]:
    """{"a, b","c"} or {a,b} -> ['a, b','c'] honoring quotes."""
    s = cell.strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    names, buf, inq = [], [], False
    for ch in s:
        if ch == '"':
            inq = not inq
        elif ch == "," and not inq:
            names.append("".join(buf).strip().strip('"').strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        names.append("".join(buf).strip().strip('"').strip())
    return [n for n in names if n]


def classify_doctype(dname: str) -> tuple[str, str]:
    low = dname.lower()
    for needle, etype, cat in DOCTYPE_RULES:
        if needle.lower() in low:
            return etype, cat
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_fold(low)).strip("_")[:40] or "other"
    return slug, "other"


def detect_wing(text: str) -> str | None:
    low = text.lower()
    for needles, label in WING_RULES:
        if any(n.lower() in low for n in needles):
            return label
    return None


def parse_property(desc: str) -> dict:
    """Best-effort flat/floor/area/rent extraction from EN-structured or Marathi free text."""
    d = {"flat": None, "floor": None, "area_text": None, "rent": None, "deposit": None, "tenure_months": None}
    # English structured labels.
    m = re.search(r"Flat No:\s*(.*?)\s*Floor No:", desc, re.I | re.S)
    if m:
        d["flat"] = m.group(1).strip()[:40]
    m = re.search(r"Floor No:\s*(.*?)\s*Building Name:", desc, re.I | re.S)
    if m:
        d["floor"] = m.group(1).strip()[:40]
    # Marathi flat: सदनिका/फ्लॅट/दुकान ... <first digit-led token> (skip the word itself + क्र/नं/:).
    if not d["flat"]:
        m = re.search(r"(?:सदनिका|फ्लॅट|दुकान)[^0-9\n]{0,30}?([0-9][0-9A-Za-z\-/]*)", desc)
        if m:
            d["flat"] = m.group(1).strip()[:40]
    # Marathi floor: NNवा/व्या/था मजला  | तळ मजला (ground)
    if not d["floor"]:
        m = re.search(r"([0-9]+)\s*(?:वा|व्या|था|ला|वी)?\s*(?:हॅबीटेबल|हॅबिटेबल)?\s*मजल", desc)
        if m:
            d["floor"] = m.group(1)
        elif "तळ मजल" in desc:
            d["floor"] = "ground"
    # Area: NN चौ.मी (sqm) or NN चौ.फूट (sqft).
    m = re.search(r"([0-9][0-9.,]*)\s*चौ\.?\s*(?:मी|मीटर)", desc)
    if m:
        d["area_text"] = m.group(1).replace(",", "") + " sqm"
    else:
        m = re.search(r"([0-9][0-9.,]*)\s*चौ\.?\s*फ", desc)
        if m:
            d["area_text"] = m.group(1).replace(",", "") + " sqft"
    # Leave & License extras.
    m = re.search(r"मासिक\s*भाडे\s*(?:रु\.?|रू\.?)?\s*([0-9,]+)", desc)
    if m:
        d["rent"] = m.group(1).replace(",", "")
    m = re.search(r"अनामत(?:\s*रक्[कमी]+)?\s*(?:रु\.?|रू\.?)?\s*([0-9,]+)", desc)
    if m:
        d["deposit"] = m.group(1).replace(",", "")
    m = re.search(r"कालावधी\s*([0-9]+)\s*महिने", desc)
    if m:
        d["tenure_months"] = m.group(1)
    return d


def to_iso_date(d: str) -> str | None:
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d.strip())
    if not m:
        return None
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"


def q(v) -> str:
    if v is None or v == "":
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def jb(d: dict) -> str:
    import json
    return "'" + json.dumps(d, ensure_ascii=False).replace("'", "''") + "'::jsonb"


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse IGR results-list snapshots into staging. Dry-run by default.")
    ap.add_argument("--snapshot-dir", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert", action="store_true")
    ap.add_argument("--max-rows", type=int, default=500)
    args = ap.parse_args()

    BUILDING = f"(SELECT building_id FROM rera_project_profiles WHERE rera_registration_number='{RERA_REG}' ORDER BY created_at LIMIT 1)"

    def counts_sql() -> str:
        return (
            f"SELECT 'records' AS item, count(*)::text FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}'"
            f"\nUNION ALL SELECT 'parties', count(*)::text FROM unit_registration_parties WHERE raw_context->>'source'='{SOURCE}'"
            f"\nUNION ALL SELECT 'units', count(*)::text FROM building_units WHERE metadata->>'source'='{SOURCE}'"
            f"\nUNION ALL SELECT 'reviews', count(*)::text FROM unit_registration_review_items WHERE raw_context->>'source'='{SOURCE}'"
            "\nORDER BY item;"
        )

    if args.revert:
        if not (args.apply and args.real_ok):
            code, cur = run_psql(counts_sql())
            print("Revert dry-run. current tagged rows (would delete):")
            print(cur)
            print("Reverting requires --revert --apply --real-ok.")
            return 0
        delete = (
            f"BEGIN;\nDELETE FROM unit_registration_review_items WHERE raw_context->>'source'='{SOURCE}';"
            f"\nDELETE FROM unit_registration_parties WHERE raw_context->>'source'='{SOURCE}';"
            f"\nDELETE FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}';"
            f"\nDELETE FROM building_units WHERE metadata->>'source'='{SOURCE}';\nCOMMIT;\n" + counts_sql()
        )
        code, out = run_psql(delete)
        print("Remaining tagged rows after revert (expect all 0):")
        print(out)
        return code

    snap = Path(args.snapshot_dir)
    files = sorted(snap.glob("capture_*.html"))
    if not files:
        print(f"No capture_*.html in {snap}")
        return 1

    # Parse + dedupe by (doc_number, sro_code).
    seen: dict[tuple, dict] = {}
    for f in files:
        for cells in parse_grid(f.read_text(encoding="utf-8", errors="replace")):
            docno, dname, rdate, sroname, seller, purchaser, propdesc, srocode, status = (cells + [""] * 10)[:9]
            key = (docno, srocode)
            if key in seen:
                continue
            etype, cat = classify_doctype(dname)
            wing = detect_wing(propdesc) or detect_wing(dname)
            seen[key] = {
                "docno": docno, "dname": dname, "rdate": rdate, "sro": sroname, "srocode": srocode,
                "status": status, "seller": seller, "purchaser": purchaser, "propdesc": propdesc,
                "etype": etype, "cat": cat, "wing": wing, "src_file": f.name,
                **parse_property(propdesc),
            }

    rows = list(seen.values())
    by_wing: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for r in rows:
        by_wing[r["wing"] or "unknown/other-building"] = by_wing.get(r["wing"] or "unknown/other-building", 0) + 1
        by_cat[r["cat"]] = by_cat.get(r["cat"], 0) + 1
    target = [r for r in rows if r["wing"] == TARGET_WING]

    print(f"Parsed {len(files)} snapshot pages -> {len(rows)} unique registrations (deduped by doc+SRO).")
    print("by wing/building:")
    for k, v in sorted(by_wing.items(), key=lambda kv: -kv[1]):
        print(f"  {v:3d}  {k}{'   <-- TARGET' if k == TARGET_WING else ''}")
    print("by document category:", ", ".join(f"{k}={v}" for k, v in sorted(by_cat.items())))
    print(f"TARGET ({TARGET_WING}) registrations to stage: {len(target)}")

    if not (args.apply and args.real_ok):
        print("\nDry run only. No DB writes. Preview of target rows:")
        for r in target[:12]:
            sellers = parse_name_array(r["seller"])
            buyers = parse_name_array(r["purchaser"])
            print(f"  doc {r['docno']} {to_iso_date(r['rdate'])} {r['etype']}/{r['cat']} "
                  f"flat={r['flat']} floor={r['floor']} area={r['area_text']} "
                  f"rent={r['rent']} | {len(sellers)} seller / {len(buyers)} purchaser")
        print("\nWriting requires --apply and --real-ok.")
        return 0

    if len(target) > args.max_rows:
        print(f"Refusing: {len(target)} target rows exceeds --max-rows={args.max_rows}.")
        return 1

    code, cur = run_psql(counts_sql())
    if any(int(l.split("|")[1]) > 0 for l in cur.splitlines() if "|" in l):
        print("Refusing: tagged rows already exist. Run --revert --apply --real-ok first.")
        print(cur)
        return 1

    stmts = ["BEGIN;"]
    for r in target:
        iso = to_iso_date(r["rdate"])
        wing_letter = "A"
        flat = r["flat"]
        tag = {"source": SOURCE, "phase": PHASE, "rera_reg": RERA_REG, "is_fake": False, "is_sample": False,
               "src_file": r["src_file"], "doctype_raw": r["dname"], "sro_raw": r["sro"],
               "status_code": r["status"], "wing_label": r["wing"], "external_calls_made": False,
               "note": "IGR results-list (Level 1) parse; price pending Index II; review-gated."}
        # building_unit upsert (by building+wing+unit_number), only if we parsed a flat number.
        unit_sub = "NULL"
        if flat:
            stmts.append(
                f"INSERT INTO building_units (building_id, building_name, wing, unit_number, canonical_status, metadata) "
                f"SELECT {BUILDING}, 'Kalpataru Radiance A', '{wing_letter}', {q(flat)}, 'active', {jb(tag)} "
                f"WHERE NOT EXISTS (SELECT 1 FROM building_units WHERE building_id={BUILDING} AND wing='{wing_letter}' "
                f"AND unit_number={q(flat)} AND metadata->>'source'='{SOURCE}');"
            )
            unit_sub = (f"(SELECT id FROM building_units WHERE building_id={BUILDING} AND wing='{wing_letter}' "
                        f"AND unit_number={q(flat)} AND metadata->>'source'='{SOURCE}' ORDER BY created_at LIMIT 1)")
        rent = r["rent"] if r["cat"] == "tenancy" else None
        deposit = r["deposit"] if r["cat"] == "tenancy" else None
        stmts.append(
            "INSERT INTO unit_registration_records (building_id, building_unit_id, doc_number, registration_year, "
            "registration_date, sro_office, document_type, transaction_category, property_description_raw, wing_text, "
            "unit_text, floor_text, area_text, tenancy_monthly_rent, tenancy_deposit, parse_confidence, "
            "verification_status, source_label, raw_context) VALUES ("
            f"{BUILDING}, {unit_sub}, {q(r['docno'])}, {iso[:4] if iso else 'NULL'}, {q(iso)}, {q(r['sro'])}, "
            f"{q(r['etype'])}, {q(r['cat'])}, {q(r['propdesc'])}, {q(r['wing'])}, {q(flat)}, {q(r['floor'])}, "
            f"{q(r['area_text'])}, {q(rent)}, {q(deposit)}, 0.55, 'parsed_candidate', "
            f"'IGR eSearch results list 2026 (CTS 260/5A)', {jb(tag)});"
        )
        rec_sub = (f"(SELECT id FROM unit_registration_records WHERE doc_number={q(r['docno'])} "
                   f"AND raw_context->>'source'='{SOURCE}' ORDER BY created_at LIMIT 1)")
        sell_role, buy_role = ROLE_BY_CATEGORY[r["cat"]]
        order = 0
        for nm in parse_name_array(r["seller"]):
            ptag = dict(tag); ptag["translit"] = translit_name(nm)
            ptype = "company" if re.search(r"llp|ltd|limited|private|pvt|bank|authority|llp|एलएलपी|लिमिटेड|बँक|प्रा", nm.lower()) else "individual"
            stmts.append(
                "INSERT INTO unit_registration_parties (unit_registration_record_id, party_role, party_name_raw, "
                f"party_name_normalized, party_type, display_order, raw_context) VALUES ({rec_sub}, '{sell_role}', "
                f"{q(nm)}, {q(translit_name(nm))}, '{ptype}', {order}, {jb(ptag)});"
            )
            order += 1
        for nm in parse_name_array(r["purchaser"]):
            ptag = dict(tag); ptag["translit"] = translit_name(nm)
            ptype = "company" if re.search(r"llp|ltd|limited|private|pvt|bank|authority|एलएलपी|लिमिटेड|बँक|प्रा", nm.lower()) else "individual"
            stmts.append(
                "INSERT INTO unit_registration_parties (unit_registration_record_id, party_role, party_name_raw, "
                f"party_name_normalized, party_type, display_order, raw_context) VALUES ({rec_sub}, '{buy_role}', "
                f"{q(nm)}, {q(translit_name(nm))}, '{ptype}', {order}, {jb(ptag)});"
            )
            order += 1
        stmts.append(
            "INSERT INTO unit_registration_review_items (building_id, unit_registration_record_id, review_type, "
            f"status, priority, decision_notes, raw_context) VALUES ({BUILDING}, {rec_sub}, "
            f"'registration_record_review', 'pending', 'normal', 'IGR list parse; verify + add price from Index II.', {jb(tag)});"
        )
    stmts.append("COMMIT;")
    stmts.append(counts_sql())

    code, out = run_psql("\n".join(stmts))
    if code != 0:
        print("DB error:")
        print(out)
        return code
    print("Staged rows (counts):")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
