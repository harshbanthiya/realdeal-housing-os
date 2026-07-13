#!/usr/bin/env python3
"""OCR the WhatsApp owner/member screenshots and append rows to the store.

Two screenshot shapes both handled:
  - "Search members"  : ~Name  /  +91 xxxxx xxxxx      (name + phone, maybe unit)
  - contact search     : OKR C 26 Kapil Gupta / (IMHO) OA 1801 IH  (unit + name)

Requires tesseract (brew install tesseract). Appends normalized rows to
consolidated_contacts.csv so the matcher picks them up on the next run.

    python3 scripts/ocr_screenshots.py            # OCR + append
    python3 scripts/ocr_screenshots.py --demo
"""
from __future__ import annotations
import argparse, csv, re, subprocess, sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "scripts"))
from extract_building_contacts import norm_phone, parse_unit, COLS  # noqa: E402

STORE = BASE / "imports/screenshot_contacts/consolidated_contacts.csv"
OCR_OUT = BASE / "imports/screenshot_contacts/ocr_screenshots.csv"
FOLDERS = [
    ("/Users/sheeed/Downloads/Data of buildings/Kalpataru R Owner Data SS", "OKR"),
    ("/Users/sheeed/Downloads/Data of buildings/Kalpataru R Tanent Data SS", "OKR"),
    ("/Volumes/RDH 5TB/RDH DATA 2024/RDH ALL Footage/Clients Data/okr", "OKR"),
    ("/Volumes/RDH 5TB/RDH DATA 2024/RDH ALL Footage/Clients Data/imho", "IH"),
]
PHONE_RX = re.compile(r"\+?\d[\d\s\-()]{8,}\d")
# unit prefix in a saved name: "OKR C 26 Name", "(IMHO) OA 1801 IH Name", "OB 105 IH"
UNIT_PREFIX = re.compile(
    r"^\W*(?:\(?IMHO\)?|\(?IMHT\)?|OKR)?\s*"
    r"(?:O?([A-D]))?\s*[- ]?\s*(\d{1,4})\b", re.I)
NAMEISH = re.compile(r"[A-Za-z]{2,}")


def clean_name(s: str) -> str:
    s = re.sub(r"^[~\s]+", "", s)
    s = re.sub(r"\b(IMHO|IMHT|OKR|IH|Home|Available|Admin)\b", " ", s, flags=re.I)
    s = re.sub(r"\bHey there.*|using WhatsApp.*", " ", s, flags=re.I)
    s = re.sub(r"[^\w .()'-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def ocr(img: Path) -> list[str]:
    r = subprocess.run(["tesseract", str(img), "-", "--psm", "6"],
                       capture_output=True, text=True)
    return [ln.rstrip() for ln in r.stdout.splitlines() if ln.strip()]


def parse_lines(lines: list[str], building: str, src: str) -> list[dict]:
    """Emit rows. Pair a phone with the nearest preceding name line; also read
    unit + name out of contact-search style names."""
    out, pending = [], None
    for raw in lines:
        pm = PHONE_RX.search(raw)
        # a line that is essentially just a phone number
        if pm and len(re.sub(r"\D", "", raw)) >= 10 and not NAMEISH.search(re.sub(r"\+?\d.*", "", raw)):
            e164, _ = norm_phone(pm.group())
            name = pending or ""
            wing, floor, unit, rest = _unit_from(name)
            if e164:
                out.append(_row(building, wing, floor, unit, clean_name(rest), e164, src))
            pending = None
            continue
        # otherwise a possible name line (maybe with inline phone + unit)
        nm = clean_name(raw)
        if not NAMEISH.search(nm) and not pm:
            continue
        if pm:  # name and phone on same line
            e164, _ = norm_phone(pm.group())
            wing, floor, unit, rest = _unit_from(re.sub(re.escape(pm.group()), " ", raw))
            if e164:
                out.append(_row(building, wing, floor, unit, clean_name(rest), e164, src))
            pending = None
        else:
            # contact-search row with unit but no phone -> still record name+unit
            wing, floor, unit, rest = _unit_from(raw)
            name = clean_name(rest)
            if unit and NAMEISH.search(name):
                out.append(_row(building, wing, floor, unit, name, "", src))
            pending = name or nm
    return out


def _unit_from(text: str):
    """Return (wing, floor, unit, name_without_unit_prefix)."""
    m = UNIT_PREFIX.match(text.strip())
    if m and m.group(2):
        wing = (m.group(1) or "").upper()
        w, f, u = parse_unit(f"{wing} {m.group(2)}")
        rest = text.strip()[m.end():]
        return w, f, u, rest
    return "", "", "", text


def _row(building, wing, floor, unit, name, e164, src):
    return {"building": building, "wing": wing, "floor": floor, "unit": unit,
            "unit_raw": f"{wing}{unit}" if unit else "", "name": name[:120],
            "phone_e164": e164, "phone_raw": "", "email": "", "role": "",
            "source_file": f"ocr/{src}", "sheet": "", "row": ""}


def demo():
    assert norm_phone("+91 98209 21479")[0] == "+919820921479"
    rows = parse_lines(["~Aman Surana", "+91 98209 21479",
                        "OKR C 26 Kapil Gupta", "OKR 649"], "OKR", "x")
    byname = {r["name"]: r for r in rows}
    assert byname["Aman Surana"]["phone_e164"] == "+919820921479"
    assert byname["Kapil Gupta"]["wing"] == "C" and byname["Kapil Gupta"]["unit"] == "26"
    w, f, u, rest = _unit_from("(IMHO) OA 1801 IH")
    assert w == "A" and u == "01" and f == "18", (w, f, u)
    print("ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()

    all_rows, per = [], []
    for folder, bld in FOLDERS:
        p = Path(folder)
        if not p.exists():
            per.append((folder, "MISSING")); continue
        imgs = [f for f in p.iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg")
                and not f.name.startswith("._")]
        got = 0
        for img in sorted(imgs):
            rows = parse_lines(ocr(img), bld, img.name)
            all_rows += rows; got += len(rows)
        per.append((folder, f"{len(imgs)} imgs -> {got} rows"))

    with OCR_OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(all_rows)
    # append to the store the matcher reads
    existing = STORE.read_text() if STORE.exists() else ""
    with STORE.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if not existing:
            w.writeheader()
        w.writerows(all_rows)

    wp = sum(1 for r in all_rows if r["phone_e164"])
    print(f"OCR rows: {len(all_rows)}  (with phone {wp})  -> appended to store")
    for folder, s in per:
        print(f"  {s:<24}  {folder.split('/')[-1]}")


if __name__ == "__main__":
    sys.exit(main())
