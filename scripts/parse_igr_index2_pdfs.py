#!/usr/bin/env python3
"""Phase 6.20 — review-gated parser: IGR Index II PDFs -> full staging records (with PRICE).

Reads a page folder of operator-downloaded IGR documents:
  - index22_* / index22_*.pdf : one Index II ("सूची क्र.2") per registration, the authoritative
    full record (consideration / market value / stamp duty / registration fee / area / parties with
    age + PAN / dates), and
  - optional "Search results of Page N.pdf" (used only to confirm the row count).

Parses each Index II by its numbered fields (1)-(14), normalizes the (Marathi/English) document type
into our category, parses the field-(4) property block for building/wing/flat/floor (+ rent/deposit/
tenure for leave-and-license), extracts seller/lessor (field 7) and purchaser/lessee (field 8) parties
(name + age + PAN), transliterates Devanagari names offline, and classifies the wing — checking
Allura/Brilliance/Lumina/Patra BEFORE Ora (since "ORA" is a substring of "ALLURA"/"ALORA").

For TARGET rows (Wing A-Ora = "Kalpataru Radiance A") it UPSERTS by (building, doc_number): any
existing record for that doc (e.g. the list-only Phase 6.19 version) is replaced with this full,
priced version. Non-target wings on the same CTS are reported but not written.

Dry-run by default. Writing requires --apply AND --real-ok. Reversible via --revert.
NO scrape/IGR/external call (reads local PDFs). Records are verification_status='parsed_candidate'.
Requires: pdftotext (poppler) + indic-transliteration.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import unicodedata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
PHASE = "6.20"
SOURCE = "igr_index2_kalpataru"
RERA_REG = "P51800000591"

DOCTYPE_RULES = [
    ("िलव्ह", "leave_and_license", "tenancy"), ("लिव्ह", "leave_and_license", "tenancy"),
    ("लायसन", "leave_and_license", "tenancy"), ("leave and licen", "leave_and_license", "tenancy"),
    ("बक्षीस", "gift_deed", "ownership"), ("gift", "gift_deed", "ownership"),
    ("सेल डीड", "sale_deed", "ownership"), ("खरेदीखत", "sale_deed", "ownership"),
    ("विक्रीपत्र", "sale_deed", "ownership"), ("sale", "sale_deed", "ownership"),
    ("करारनामा", "agreement_to_sell", "ownership"),
    ("deposit of title deeds", "mortgage", "encumbrance"), ("गहाण", "mortgage", "encumbrance"),
    ("conveyance", "conveyance", "ownership"), ("अभिहस्तांतरण", "conveyance", "ownership"),
]
ROLE_BY_CATEGORY = {
    "ownership": ("seller", "purchaser"), "tenancy": ("lessor", "lessee"),
    "encumbrance": ("mortgagee", "mortgagor"), "other": ("seller", "purchaser"),
}

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
PAN_RE = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
# watermark fragments pdftotext interleaves ("For Preview Only"): drop isolated 1-char latin tokens.


def read_env_value(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    with ENV_FILE.open(encoding="utf-8") as h:
        for line in h:
            if line.startswith(f"{key}="):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def run_psql(sql: str) -> tuple[int, str]:
    u, p, d = read_env_value("POSTGRES_USER"), read_env_value("POSTGRES_PASSWORD"), read_env_value("POSTGRES_DB")
    if not (u and p and d):
        return 1, "Missing POSTGRES_* in docker/.env."
    cmd = ["docker", "exec", "-i", "-e", f"PGPASSWORD={p}", "realdeal-postgres", "psql",
           "-U", u, "-d", d, "-v", "ON_ERROR_STOP=1", "-At", "-F", "|"]
    r = subprocess.run(cmd, input=sql, text=True, capture_output=True, check=False)
    return r.returncode, r.stdout.strip() or r.stderr.strip()


try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate as _tr
    _HAVE_TR = True
except Exception:  # noqa: BLE001
    _HAVE_TR = False


def ascii_fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def translit(raw: str) -> str:
    if not raw:
        return ""
    if DEVANAGARI.search(raw) and _HAVE_TR:
        try:
            raw = _tr(raw, sanscript.DEVANAGARI, sanscript.IAST)
        except Exception:  # noqa: BLE001
            pass
    return re.sub(r"\s+", " ", ascii_fold(raw)).strip().lower()


def pdftext(path: Path) -> str:
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=False)
    return r.stdout or ""


def clean_frag(s: str) -> str:
    """Drop isolated watermark letters and collapse whitespace."""
    s = re.sub(r"\s+", " ", s)
    # remove isolated single latin letters surrounded by spaces (watermark) but keep PANs/words
    s = re.sub(r"(?<=\s)[a-zA-Z](?=\s)", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def num(s: str) -> str | None:
    m = re.search(r"([0-9][0-9,]*\.?[0-9]*)", s or "")
    return m.group(1).replace(",", "") if m else None


def split_fields(text: str) -> dict:
    """Split Index II text into {field_number: content} using the (1)..(14) markers."""
    parts = re.split(r"\((1[0-4]|[1-9])\)", text)
    fields: dict[int, str] = {}
    # parts: [pre, '1', content1, '2', content2, ...]
    for i in range(1, len(parts) - 1, 2):
        try:
            n = int(parts[i])
        except ValueError:
            continue
        fields[n] = parts[i + 1]
    fields["_head"] = parts[0]
    return fields


WING_CHECKS = [
    ("Wing C-Allura", ("विंग सी", "wing c", "अलोरा", "अल्लोरा", "अल्लुरा", "एल्लूरा", "allura", "allure", "alora", "allora")),
    ("Wing B-Brilliance", ("विंग बी", "wing b", "ब्रिलियन्स", "ब्रिल्लीयन्स", "ब्रिलीयन्स", "brilliance")),
    ("Wing D-Lumina", ("विंग डी", "wing d", "लुमिना", "लुमीना", "lumina")),
    ("Patra Chawl (MHADA rehab)", ("पत्रा चाळ", "patra chawl")),
    ("Wing A-Ora", ("विंग ए", "wing a", "टॉवर ए", "tower a", "ए - ओरा", "ए-ओरा", "ए ओरा", "a ora", "a-ora", "tower ora", "- ओरा")),
]


def skeleton(s: str) -> str:
    """Drop Devanagari marks/whitespace so pdftotext's visual-order matra reordering (विंग->िवंग)
    doesn't defeat substring matching; lowercase for Latin."""
    return "".join(c for c in s if unicodedata.category(c)[0] != "M" and not c.isspace()).lower()


def detect_wing(prop_text: str) -> str | None:
    sk = skeleton(prop_text)
    for label, needles in WING_CHECKS:
        if any(skeleton(n) in sk for n in needles):
            return label
    return None


def classify_doctype(t: str) -> tuple[str, str]:
    sk = skeleton(t)
    for needle, et, cat in DOCTYPE_RULES:
        if skeleton(needle) in sk:
            return et, cat
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_fold(t.lower())).strip("_")[:40] or "other"
    return slug, "other"


def parse_parties(block: str) -> list[dict]:
    """From field 7/8: entries like '1): नाव:-NAME वय:-NN पत्ता:-... पॅन नं:-PPPPP'."""
    block = clean_frag(block)
    out = []
    # split on entry numbering 1): 2): 3):
    chunks = re.split(r"\b\d+\)\s*:", block)
    for ch in chunks:
        if "नाव" not in ch:
            continue
        m = re.search(r"नाव\s*:\-?\s*(.+?)\s*वय\s*:", ch)
        name = m.group(1).strip() if m else None
        if not name:
            m2 = re.search(r"नाव\s*:\-?\s*(.+?)\s*(?:पत्ता|पॅन)", ch)
            name = m2.group(1).strip() if m2 else None
        if not name:
            continue
        agem = re.search(r"वय\s*:\-?\s*(\d+)", ch)
        age = agem.group(1) if agem else None
        pan = PAN_RE.search(ch)
        addr = re.search(r"पत्ता\s*:\-?\s*(.+?)(?:\s*पॅन|\s*$)", ch)
        out.append({
            "name": name[:200], "age": age, "pan": pan.group(1) if pan else None,
            "address": (addr.group(1).strip()[:400] if addr else None),
        })
    return out


def parse_property(field4: str) -> dict:
    t = clean_frag(field4)
    d = {"flat": None, "floor": None, "building": None, "rent": None, "deposit": None, "tenure_months": None, "raw": t[:1200]}
    m = re.search(r"सद\s?िनका\s*(?:नं|क्रं|क्र|क्रमांक)?\.?\s*[:]?\s*([0-9][0-9A-Za-z\-/]*)", t) or \
        re.search(r"(?:सदनिका|फ्लॅट|दुकान)[^0-9\n]{0,30}?([0-9][0-9A-Za-z\-/]*)", t)
    if m:
        d["flat"] = m.group(1)[:40]
    if re.search(r"पिहला मजला|पहिला मजला", t):
        d["floor"] = "1"
    else:
        m = re.search(r"([0-9]+)\s*(?:वा|व्या|था|ला)?\s*मजल", t)
        if m:
            d["floor"] = m.group(1)
        elif "तळ मजल" in t:
            d["floor"] = "ground"
    m = re.search(r"इमारतीचे नाव\s*[:]?\s*([^,]{2,60})", t)
    if m:
        d["building"] = m.group(1).strip()
    m = re.search(r"मािसक भाडे\s*(?:रु\.?|रू\.?)?\s*([0-9,]+)", t) or re.search(r"मासिक भाडे\s*(?:रु\.?|रू\.?)?\s*([0-9,]+)", t)
    if m:
        d["rent"] = m.group(1).replace(",", "")
    m = re.search(r"अनामत(?:\s*रक्[कमी]+)?\s*(?:रु\.?|रू\.?)?\s*([0-9,]+)", t)
    if m:
        d["deposit"] = m.group(1).replace(",", "")
    m = re.search(r"कालावधी\s*([0-9]+)\s*मिहन्|कालावधी\s*([0-9]+)\s*महिन", t)
    if m:
        d["tenure_months"] = m.group(1) or m.group(2)
    return d


def parse_index2(path: Path) -> dict | None:
    text = pdftext(path)
    if "दस्त क्रमांक" not in text and "सूची" not in text:
        return None
    m = re.search(r"दस्त क्रमांक\s*[:：]?\s*([0-9]+)\s*/\s*([0-9]{4})", text)
    docno = m.group(1) if m else None
    year = m.group(2) if m else None
    f = split_fields(text)
    dtype_raw = clean_frag(f.get(1, "")).split(" ")[0:6]
    dtype_raw = " ".join(dtype_raw)[:60]
    etype, cat = classify_doctype(dtype_raw)
    consideration = num(f.get(2, ""))
    market_value = num(f.get(3, ""))
    prop = parse_property(f.get(4, ""))
    area = clean_frag(f.get(5, ""))[:60]
    sellers = parse_parties(f.get(7, ""))
    purchasers = parse_parties(f.get(8, ""))
    de = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(9, ""))
    dr = re.search(r"([0-3]?\d/[01]?\d/\d{4})", f.get(10, ""))
    stamp = num(f.get(12, ""))
    regfee = num(f.get(13, ""))
    wing = detect_wing(f.get(4, "")) or detect_wing(text)
    return {
        "file": path.name, "doc_no": docno, "year": year, "dtype_raw": dtype_raw, "etype": etype, "cat": cat,
        "consideration": consideration, "market_value": market_value, "stamp_duty": stamp, "reg_fee": regfee,
        "area": area, "wing": wing, "date_exec": de.group(1) if de else None, "date_reg": dr.group(1) if dr else None,
        "sellers": sellers, "purchasers": purchasers, **{f"prop_{k}": v for k, v in prop.items()},
    }


def iso(d: str | None) -> str | None:
    if not d:
        return None
    m = re.match(r"([0-3]?\d)/([01]?\d)/(\d{4})", d)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def q(v) -> str:
    return "NULL" if v in (None, "") else "'" + str(v).replace("'", "''") + "'"


def jb(d: dict) -> str:
    return "'" + json.dumps(d, ensure_ascii=False).replace("'", "''") + "'::jsonb"


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse IGR Index II PDFs into staging (with price). Dry-run by default.")
    ap.add_argument("--page-dir", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    BUILDING = f"(SELECT building_id FROM rera_project_profiles WHERE rera_registration_number='{RERA_REG}' ORDER BY created_at LIMIT 1)"

    def counts_sql() -> str:
        return (f"SELECT 'records', count(*)::text FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}'"
                f"\nUNION ALL SELECT 'parties', count(*)::text FROM unit_registration_parties WHERE raw_context->>'source'='{SOURCE}'"
                f"\nUNION ALL SELECT 'units', count(*)::text FROM building_units WHERE metadata->>'source'='{SOURCE}'"
                f"\nUNION ALL SELECT 'priced', count(*)::text FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}' AND consideration_amount IS NOT NULL\nORDER BY 1;")

    if args.revert:
        if not (args.apply and args.real_ok):
            _, cur = run_psql(counts_sql()); print("Revert dry-run (would delete):\n" + cur + "\nNeeds --revert --apply --real-ok.")
            return 0
        d = (f"BEGIN;\nDELETE FROM unit_registration_parties WHERE raw_context->>'source'='{SOURCE}';"
             f"\nDELETE FROM unit_registration_records WHERE raw_context->>'source'='{SOURCE}';"
             f"\nDELETE FROM building_units WHERE metadata->>'source'='{SOURCE}';\nCOMMIT;\n" + counts_sql())
        _, out = run_psql(d); print("After revert:\n" + out); return 0

    pdir = Path(args.page_dir)
    files = sorted([p for p in pdir.iterdir() if p.name.lower().startswith("index22")])
    if not files:
        print(f"No index22* files in {pdir}"); return 1
    parsed = [r for r in (parse_index2(p) for p in files) if r]

    by_wing: dict[str, int] = {}
    for r in parsed:
        by_wing[r["wing"] or "other/unknown"] = by_wing.get(r["wing"] or "other/unknown", 0) + 1
    target = [r for r in parsed if r["wing"] == "Wing A-Ora"]

    print(f"Parsed {len(parsed)} Index II PDFs from {pdir.name}.")
    for k, v in sorted(by_wing.items(), key=lambda kv: -kv[1]):
        print(f"  {v:2d}  {k}{'   <-- TARGET' if k == 'Wing A-Ora' else ''}")
    print(f"\nAll docs (price):")
    for r in parsed:
        print(f"  doc {r['doc_no']}/{r['year']} {r['etype']:18s} {r['wing'] or 'other':24s} "
              f"flat={r['prop_flat']} consid={r['consideration']} mktval={r['market_value']} stamp={r['stamp_duty']} "
              f"{len(r['sellers'])}s/{len(r['purchasers'])}p")
    print(f"\nTARGET (Wing A-Ora) to stage with price: {len(target)}")

    if not (args.apply and args.real_ok):
        print("\nDry run only. No DB writes. Writing requires --apply --real-ok.")
        return 0

    # Which target docs already exist for this building (e.g. Phase 6.19 list-only, with good names)?
    existing = set()
    if target:
        docnos = ",".join(q(r["doc_no"]) for r in target if r["doc_no"])
        _, ex = run_psql(f"SELECT doc_number FROM unit_registration_records WHERE building_id={BUILDING} "
                         f"AND doc_number IN ({docnos});")
        existing = {l.strip() for l in ex.splitlines() if l.strip()}

    stmts = ["BEGIN;"]
    for r in target:
        flat = r["prop_flat"]
        tag = {"source": SOURCE, "phase": PHASE, "rera_reg": RERA_REG, "is_fake": False, "is_sample": False,
               "src_file": r["file"], "doctype_raw": r["dtype_raw"], "wing_label": r["wing"],
               "market_value": r["market_value"], "stamp_duty": r["stamp_duty"], "reg_fee": r["reg_fee"],
               "area_field5": r["area"], "external_calls_made": False,
               "note": "IGR Index II PDF parse (Level 2, price); review-gated."}
        cons0 = r["consideration"] if r["consideration"] not in (None, "0") else None
        rent0 = r["prop_rent"] if r["cat"] == "tenancy" else None
        dep0 = r["prop_deposit"] if r["cat"] == "tenancy" else None
        # If the doc already exists (good HTML names), UPDATE price fields only — don't touch names.
        if r["doc_no"] in existing:
            stmts.append(
                "UPDATE unit_registration_records SET "
                f"consideration_amount=COALESCE({q(cons0)},consideration_amount), "
                f"market_value=COALESCE({q(r['market_value'])},market_value), "
                f"stamp_duty=COALESCE({q(r['stamp_duty'])},stamp_duty), "
                f"tenancy_monthly_rent=COALESCE({q(rent0)},tenancy_monthly_rent), "
                f"tenancy_deposit=COALESCE({q(dep0)},tenancy_deposit), "
                f"area_text=COALESCE(area_text,{q(r['area'])}), parse_confidence=0.7, "
                "raw_context=raw_context || "
                + jb({"index2_price_added": True, "index2_src_file": r["file"], "reg_fee": r["reg_fee"],
                      "market_value": r["market_value"], "stamp_duty": r["stamp_duty"]})
                + f" WHERE building_id={BUILDING} AND doc_number={q(r['doc_no'])};")
            continue
        unit_sub = "NULL"
        if flat:
            stmts.append(
                f"INSERT INTO building_units (building_id, building_name, wing, unit_number, canonical_status, metadata) "
                f"SELECT {BUILDING}, 'Kalpataru Radiance A', 'A', {q(flat)}, 'active', {jb(tag)} "
                f"WHERE NOT EXISTS (SELECT 1 FROM building_units WHERE building_id={BUILDING} AND wing='A' AND unit_number={q(flat)} AND metadata->>'source'='{SOURCE}');")
            unit_sub = (f"(SELECT id FROM building_units WHERE building_id={BUILDING} AND wing='A' AND unit_number={q(flat)} "
                        f"AND metadata->>'source'='{SOURCE}' ORDER BY created_at LIMIT 1)")
        cons = r["consideration"] if r["consideration"] not in (None, "0") else None
        rent = r["prop_rent"] if r["cat"] == "tenancy" else None
        dep = r["prop_deposit"] if r["cat"] == "tenancy" else None
        d_reg = iso(r["date_reg"]) or iso(r["date_exec"])
        stmts.append(
            "INSERT INTO unit_registration_records (building_id, building_unit_id, doc_number, registration_year, "
            "registration_date, sro_office, document_type, transaction_category, property_description_raw, wing_text, "
            "unit_text, floor_text, area_text, consideration_amount, market_value, stamp_duty, tenancy_monthly_rent, "
            "tenancy_deposit, parse_confidence, verification_status, source_label, raw_context) VALUES ("
            f"{BUILDING}, {unit_sub}, {q(r['doc_no'])}, {r['year'] or 'NULL'}, {q(d_reg)}, NULL, {q(r['etype'])}, "
            f"{q(r['cat'])}, {q(r['prop_raw'])}, {q(r['wing'])}, {q(flat)}, {q(r['prop_floor'])}, {q(r['area'])}, "
            f"{q(cons)}, {q(r['market_value'])}, {q(r['stamp_duty'])}, {q(rent)}, {q(dep)}, 0.7, 'parsed_candidate', "
            f"'IGR Index II PDF 2026 (CTS 260/5A)', {jb(tag)});")
        rec = (f"(SELECT id FROM unit_registration_records WHERE doc_number={q(r['doc_no'])} AND building_id={BUILDING} "
               f"AND raw_context->>'source'='{SOURCE}' ORDER BY created_at LIMIT 1)")
        srole, brole = ROLE_BY_CATEGORY[r["cat"]]
        order = 0
        for party, role in [(p, srole) for p in r["sellers"]] + [(p, brole) for p in r["purchasers"]]:
            ptag = dict(tag); ptag.update({"age": party["age"], "pan": party["pan"], "translit": translit(party["name"])})
            ptype = "company" if re.search(r"llp|ltd|limited|private|pvt|bank|authority|एलएलपी|लिमिटेड|बँक|प्रा", party["name"].lower()) else "individual"
            stmts.append(
                "INSERT INTO unit_registration_parties (unit_registration_record_id, party_role, party_name_raw, "
                f"party_name_normalized, party_type, display_order, raw_context) VALUES ({rec}, '{role}', "
                f"{q(party['name'])}, {q(translit(party['name']))}, '{ptype}', {order}, {jb(ptag)});")
            order += 1
        stmts.append(
            "INSERT INTO unit_registration_review_items (building_id, unit_registration_record_id, review_type, status, "
            f"priority, decision_notes, raw_context) VALUES ({BUILDING}, {rec}, 'registration_record_review', 'pending', "
            f"'normal', 'IGR Index II parse with price; verify parties/PAN.', {jb(tag)});")
    stmts.append("COMMIT;")
    stmts.append(counts_sql())
    code, out = run_psql("\n".join(stmts))
    print("Staged (counts):\n" + out if code == 0 else "DB error:\n" + out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
