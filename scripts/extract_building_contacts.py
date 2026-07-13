#!/usr/bin/env python3
"""Consolidate Imperial Heights / Kalpataru Radiance contacts from every source.

Reads the drive inventory (drive_inventory.csv), keeps the RAW contact-source
spreadsheets (skips our own pipeline outputs, IGR dumps, zapkey, temp files),
extracts EVERY sheet of every xls/xlsx and every csv, auto-detects the
name/phone/email/unit columns, and writes one normalized row set:

    imports/screenshot_contacts/consolidated_contacts.csv
      building,wing,floor,unit,unit_raw,name,phone_e164,phone_raw,email,role,source_file,sheet,row

The screenshot extract (extracted.csv) is folded in too, so all sources land in
one place, separated by building / wing / floor / unit / name / contact. No DB
writes -- matching is a later step.

    python3 scripts/extract_building_contacts.py            # extract all
    python3 scripts/extract_building_contacts.py --demo     # self-check
"""
from __future__ import annotations
import argparse, csv, hashlib, re, sys
from pathlib import Path

ROOT = Path("/Volumes/RDH 5TB")
BASE = Path(__file__).resolve().parents[1]
INV = BASE / "imports/screenshot_contacts/drive_inventory.csv"
OUT = BASE / "imports/screenshot_contacts/consolidated_contacts.csv"
SHOTS = BASE / "imports/screenshot_contacts/extracted.csv"

# Derived / non-contact sources to skip (our own pipeline artifacts, registration dumps).
SKIP = re.compile(
    r"normalized_contacts_|rejected_contacts_|duplicate_report_|cleaned_contacts_|"
    r"SearchResult4|/exports/igr|zapkey|/\~\$|/exports/archive_profiles/",
    re.I,
)
COLS = ["building", "wing", "floor", "unit", "unit_raw", "name",
        "phone_e164", "phone_raw", "email", "role", "source_file", "sheet", "row"]

# --- header detection -------------------------------------------------------
NAME_H = re.compile(r"\b(name|owner|tenant|party|contact person|customer)\b", re.I)
PHONE_H = re.compile(r"\b(phone|mobile|contact\s*(no|number)?|cell|whats\s*app|tel)\b", re.I)
EMAIL_H = re.compile(r"\b(e-?mail|mail id|email)\b", re.I)
UNIT_H = re.compile(r"\b(flat|unit|apt|apartment|door|premise)\b", re.I)
WING_H = re.compile(r"\b(wing|tower|building|block)\b", re.I)
ROLE_RX = re.compile(r"\b(owner|tenant|broker|buyer|seller|member|admin)\b", re.I)


def norm_phone(raw: str) -> tuple[str | None, str]:
    """(e164, reason). Indian 10-digit -> +91; keeps other-country as-is if plausible."""
    s = str(raw or "")
    m = re.search(r"\+?\d[\d\s\-()]{6,}", s)
    if not m:
        return None, "no_digits"
    digits = re.sub(r"\D", "", m.group())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return "+91" + digits, "in_mobile"
    if 11 <= len(digits) <= 15:            # already has a country code
        return "+" + digits, "intl"
    return None, "unparseable"


def parse_unit(raw: str) -> tuple[str, str, str]:
    """'A-3404' -> ('A','34','04'); 'C-804' -> ('C','8','04'); 'A-82' -> ('A','','82').

    Returns (wing, floor, unit). Floor-based numbers (>=3 digits) split as
    floor=all-but-last-2, unit=last-2. Short numbers stay as bare unit (society
    sequential style) with floor unknown.
    """
    s = str(raw or "").strip().upper()
    wm = re.search(r"\b([A-D])\b|\b([A-D])[\s\-]?\d", s)
    wing = ""
    m = re.match(r"\s*([A-D])[\s\-]*?(\d{1,4})", s)
    if m:
        wing = m.group(1)
        num = m.group(2)
    else:
        nm = re.search(r"\d{1,4}", s)
        num = nm.group() if nm else ""
    if len(num) >= 3:
        return wing, num[:-2], num[-2:]
    return wing, "", num


def building_of(path: str) -> str:
    l = path.lower()
    ih = "imperial" in l
    okr = any(x in l for x in ("kalpataru", "kallataru", "radiance"))
    return "IH" if ih and not okr else "OKR" if okr and not ih else "?"


def find_header(rows: list[list], scan: int = 8) -> tuple[int, dict]:
    """Locate the header row and map roles -> column index. -1 if none found."""
    best_i, best_map, best_score = -1, {}, 0
    for i, row in enumerate(rows[:scan]):
        cells = [str(c or "") for c in row]
        cmap, score = {}, 0
        for j, c in enumerate(cells):
            if "name" not in cmap and NAME_H.search(c):
                cmap["name"] = j; score += 1
            if "phone" not in cmap and PHONE_H.search(c):
                cmap["phone"] = j; score += 1
            elif "phone2" not in cmap and PHONE_H.search(c) and cmap.get("phone") != j:
                cmap["phone2"] = j
            if "email" not in cmap and EMAIL_H.search(c):
                cmap["email"] = j
            if "unit" not in cmap and UNIT_H.search(c):
                cmap["unit"] = j
            if "wing" not in cmap and WING_H.search(c):
                cmap["wing"] = j
        if score > best_score:
            best_i, best_map, best_score = i, cmap, score
    return (best_i, best_map) if best_score >= 1 else (-1, {})


def emit_rows(grid, building, source, sheet, out):
    """Pull normalized contact rows from a 2-D cell grid."""
    grid = [r for r in grid if any(str(c or "").strip() for c in r)]
    if not grid:
        return 0
    hi, cmap = find_header(grid)
    n = 0
    for r in grid[hi + 1:] if hi >= 0 else grid:
        cells = [str(c or "").strip() for c in r]
        def get(key):
            j = cmap.get(key)
            return cells[j] if j is not None and j < len(cells) else ""
        name = get("name")
        unit_raw = get("unit") or get("wing")
        phone_raw = get("phone") or get("phone2")
        email = get("email")
        # Fallback when header detection failed: scan the whole row.
        joined = " ".join(cells)
        if not phone_raw:
            phone_raw = joined
        e164, _ = norm_phone(phone_raw)
        if not unit_raw:
            um = re.search(r"\b[A-D][\s\-]?\d{2,4}\b", joined)
            unit_raw = um.group() if um else ""
        if not name:
            # first non-numeric, non-unit cell that looks like a name
            for c in cells:
                if c and not re.fullmatch(r"[\d\s\-+()./]+", c) and not re.fullmatch(r"[A-D][\s\-]?\d{2,4}", c.upper()):
                    name = c; break
        if not (e164 or (name and unit_raw)):
            continue
        role_m = ROLE_RX.search(joined)
        wing, floor, unit = parse_unit(unit_raw)
        out.append({
            "building": building, "wing": wing, "floor": floor, "unit": unit,
            "unit_raw": unit_raw, "name": name[:120],
            "phone_e164": e164 or "", "phone_raw": phone_raw[:40] if not e164 else "",
            "email": email if EMAIL_H or "@" in email else "",
            "role": (role_m.group().lower() if role_m else ""),
            "source_file": source, "sheet": sheet, "row": "",
        })
        n += 1
    return n


def read_csv_grid(p: Path):
    with p.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        return [row for row in csv.reader(f)]


def read_xls_sheets(p: Path):
    """Yield (sheet_name, grid) for xlsx (openpyxl) or xls (xlrd)."""
    if p.suffix.lower() == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
        for ws in wb.worksheets:
            yield ws.title, [list(r) for r in ws.iter_rows(values_only=True)]
    else:
        import xlrd
        wb = xlrd.open_workbook(p)
        for ws in wb.sheets():
            yield ws.name, [ws.row_values(i) for i in range(ws.nrows)]


def demo():
    assert norm_phone("9820202309")[0] == "+919820202309"
    assert norm_phone("+91 98202 02309")[0] == "+919820202309"
    assert norm_phone("022 2266 8991")[0] is None          # landline
    assert norm_phone("+971 50 651 3875")[0] == "+971506513875"
    assert parse_unit("A-3404") == ("A", "34", "04"), parse_unit("A-3404")
    assert parse_unit("C-804") == ("C", "8", "04"), parse_unit("C-804")
    assert parse_unit("D-102") == ("D", "1", "02")
    assert parse_unit("A-82") == ("A", "", "82")
    assert parse_unit("Flat 1602 B Wing")[0] in ("B", "")   # tolerant
    grid = [["Owner Name", "Flat No", "Mobile"],
            ["Ramesh Shah", "A-3404", "9820202309"],
            ["", "", ""]]
    out = []
    assert emit_rows(grid, "IH", "x.xlsx", "S1", out) == 1
    assert out[0]["name"] == "Ramesh Shah" and out[0]["floor"] == "34" and out[0]["phone_e164"] == "+919820202309"
    print("ok")


def fold_screenshots(out):
    if not SHOTS.exists():
        return 0
    n = 0
    for r in csv.DictReader(SHOTS.open()):
        wing, floor, unit = parse_unit(r.get("subtitle", ""))
        role = ROLE_RX.search(r.get("subtitle", "") or "")
        out.append({
            "building": "IH", "wing": wing, "floor": floor, "unit": unit,
            "unit_raw": r.get("subtitle", ""), "name": r.get("saved_name", ""),
            "phone_e164": r.get("phone", ""), "phone_raw": "", "email": "",
            "role": role.group().lower() if role else "",
            "source_file": "screenshots/" + r.get("source_img", ""), "sheet": "", "row": "",
        })
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()

    targets = []
    for r in csv.DictReader(INV.open()):
        if r["ext"] not in ("xls", "xlsx", "csv"):
            continue
        if SKIP.search("/" + r["path"]) or int(r["bytes"] or 0) == 0:
            continue
        targets.append(r["path"])

    out, errors, per_file = [], [], []
    for rel in targets:
        p = ROOT / rel
        b = building_of(rel)
        try:
            if p.suffix.lower() == ".csv":
                got = emit_rows(read_csv_grid(p), b, rel, "", out)
                per_file.append((rel, "", got))
            else:
                for sheet, grid in read_xls_sheets(p):
                    got = emit_rows(grid, b, rel, sheet, out)
                    per_file.append((rel, sheet, got))
        except Exception as e:
            errors.append((rel, repr(e)[:90]))

    shots = fold_screenshots(out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader(); w.writerows(out)

    with_phone = sum(1 for r in out if r["phone_e164"])
    with_unit = sum(1 for r in out if r["unit_raw"])
    print(f"files scanned : {len(targets)}  (+{len(per_file)} sheets)")
    print(f"rows extracted: {len(out)}  ->  {OUT}")
    print(f"  with phone  : {with_phone}")
    print(f"  with unit   : {with_unit}")
    print(f"  from shots  : {shots}")
    print(f"  IH / OKR    : {sum(1 for r in out if r['building']=='IH')} / {sum(1 for r in out if r['building']=='OKR')}")
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for rel, e in errors[:20]:
            print(f"  {e}  <- {rel}")


if __name__ == "__main__":
    sys.exit(main())
