#!/usr/bin/env python3
"""Parse an iPhone Contacts export (.vcf / vCard) into building/wing/unit/role/name/phone.

The salesperson saves contacts encoded like the WhatsApp groups:
    OKR C 26 Kapil Gupta            -> OKR owner, wing C unit 26, Kapil Gupta
    (IMHO) OA 1801 IH               -> IH owner,  wing A unit 1801
    IMHT B-2501 Ramchand Kishnani   -> IH tenant, wing B unit 2501
    WaBrk / Brk Ashok               -> broker

Export the phone's contacts to a single .vcf (see the header notes in chat),
drop it anywhere, then:

    python3 scripts/parse_iphone_vcf.py /path/to/contacts.vcf
    python3 scripts/parse_iphone_vcf.py /path/to/contacts.vcf --append   # into the store
    python3 scripts/parse_iphone_vcf.py --demo

Output: imports/screenshot_contacts/iphone_contacts.csv (building,wing,floor,unit,
unit_raw,name,phone_e164,phone_raw,email,role,source_file,sheet,row).
"""
from __future__ import annotations
import argparse, csv, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "scripts"))
from extract_building_contacts import norm_phone, parse_unit, COLS  # noqa: E402

OUT = BASE / "imports/screenshot_contacts/iphone_contacts.csv"
STORE = BASE / "imports/screenshot_contacts/consolidated_contacts.csv"

# role codes, tried in order (first hit wins)
ROLE_RULES = [
    (re.compile(r"\bIMHT\b|\bTKR\b|\btenant|\btanent|\bT[- ]?[A-D]\d", re.I), "tenant"),
    (re.compile(r"\bIMHO\b|\bOKR\b|\bO[A-D]\b|\bowner", re.I), "owner"),
    (re.compile(r"wabrk|\bbrk\b|broker|\bRDH\b", re.I), "broker"),
    (re.compile(r"\bclient\b", re.I), "client"),
]
BUILDING_RULES = [
    (re.compile(r"\bOKR\b|kalpataru|kallataru|radiance|ora tower|\bTKR\b", re.I), "OKR"),
    (re.compile(r"\bIMHO\b|\bIMHT\b|\bIH\b|imperial", re.I), "IH"),
]
# unit code: optional owner/tenant letter O/T then wing A-D then number; or wing-number
UNIT_RX = re.compile(r"\b[OT]?([A-D])\s*[- ]?\s*(\d{2,4})\b")


def role_of(name: str) -> str:
    for rx, role in ROLE_RULES:
        if rx.search(name):
            return role
    return ""


def building_of(name: str) -> str:
    for rx, b in BUILDING_RULES:
        if rx.search(name):
            return b
    return ""


def unit_of(name: str):
    """Return (wing, floor, FULL unit number). Keep the whole number (e.g. 4204)
    -- the DB's building_units.unit_number is the full floor-based number, so
    splitting it into floor/unit would break unit matching."""
    m = UNIT_RX.search(name)
    if not m:
        return "", "", ""
    wing, num = m.group(1).upper(), m.group(2)
    floor = num[:-2] if len(num) >= 3 else ""
    return wing, floor, num


def clean_person(name: str) -> str:
    s = re.sub(r"\(?\b(IMHO|IMHT|OKR|TKR|IH|WaBrk|Brk|RDH|Owner|Tenant|Tanent|Client)\b\)?",
               " ", name, flags=re.I)
    s = re.sub(r"\b[OT]?[A-D]\s*[- ]?\s*\d{2,4}\b", " ", s)   # strip unit code
    s = re.sub(r"[^\w .'-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_vcards(text: str) -> list[dict]:
    """Minimal vCard reader: unfold folded lines, then split on BEGIN/END:VCARD."""
    # RFC6350 line folding: a CRLF followed by space/tab continues the prior line.
    text = re.sub(r"\r?\n[ \t]", "", text)
    rows = []
    for block in re.split(r"BEGIN:VCARD", text, flags=re.I)[1:]:
        fn = ""
        for pat in (r"^FN[^:]*:(.+)$", r"^N[^:]*:(.+)$", r"^ORG[^:]*:(.+)$"):
            m = re.search(pat, block, re.I | re.M)
            if m:
                fn = m.group(1).replace(";", " ").strip()
                break
        note = " ".join(re.findall(r"^NOTE[^:]*:(.+)$", block, re.I | re.M))
        tels = re.findall(r"^TEL[^:]*:(.+)$", block, re.I | re.M)
        hay = f"{fn} {note}"
        b = building_of(hay)
        role = role_of(hay)
        wing, floor, unit = unit_of(hay)
        person = clean_person(fn)
        phones = [norm_phone(t)[0] for t in tels]
        phones = [p for p in phones if p] or [None]
        for ph in phones:
            if not (ph or person):
                continue
            rows.append({
                "building": b, "wing": wing, "floor": floor, "unit": unit,
                "unit_raw": f"{wing}{unit}" if unit else "", "name": person[:120],
                "phone_e164": ph or "", "phone_raw": "", "email": "", "role": role,
                "source_file": "iphone_vcf", "sheet": "", "row": "",
            })
    return rows


def demo():
    vcf = (
        "BEGIN:VCARD\nFN:OKR C 26 Kapil Gupta\nTEL;type=CELL:+91 98200 12345\nEND:VCARD\n"
        "BEGIN:VCARD\nFN:(IMHO) OA 1801 IH\nTEL:+919820055555\nEND:VCARD\n"
        "BEGIN:VCARD\nFN:IMHT B-2501 Ramchand Kishnani\nTEL:098201 99999\nEND:VCARD\n"
        "BEGIN:VCARD\nFN:Brk Ashok Shinde\nTEL:+91 90000 11111\nEND:VCARD\n"
    )
    rows = parse_vcards(vcf)
    by = {r["name"]: r for r in rows}
    assert by["Kapil Gupta"]["building"] == "OKR" and by["Kapil Gupta"]["role"] == "owner"
    assert by["Kapil Gupta"]["wing"] == "C" and by["Kapil Gupta"]["unit"] == "26"
    assert by["Kapil Gupta"]["phone_e164"] == "+919820012345"
    ih = [r for r in rows if r["building"] == "IH" and r["role"] == "owner"][0]
    assert ih["wing"] == "A" and ih["floor"] == "18" and ih["unit"] == "1801", ih
    ten = [r for r in rows if r["role"] == "tenant"][0]
    assert ten["wing"] == "B" and ten["unit"] == "2501" and ten["name"] == "Ramchand Kishnani"
    assert any(r["role"] == "broker" for r in rows)
    print("ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vcf", nargs="?")
    ap.add_argument("--append", action="store_true", help="append into the matcher store")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    if not a.vcf:
        ap.error("give a .vcf path (or --demo)")
    rows = parse_vcards(Path(a.vcf).read_text(errors="replace"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
    if a.append:
        with STORE.open("a", newline="") as f:
            csv.DictWriter(f, fieldnames=COLS).writerows(rows)
    b = lambda x: sum(1 for r in rows if r["building"] == x)
    named_unit = sum(1 for r in rows if r["unit_raw"] and r["name"])
    print(f"contacts parsed : {len(rows)}  -> {OUT}")
    print(f"  with phone    : {sum(1 for r in rows if r['phone_e164'])}")
    print(f"  with unit     : {sum(1 for r in rows if r['unit_raw'])}   (unit+name: {named_unit})")
    print(f"  IH / OKR / ?  : {b('IH')} / {b('OKR')} / {sum(1 for r in rows if not r['building'])}")
    from collections import Counter
    print("  roles         :", dict(Counter(r["role"] or "-" for r in rows)))
    if a.append:
        print("appended to store -> re-run scripts/match_building_contacts.py")


if __name__ == "__main__":
    sys.exit(main())
