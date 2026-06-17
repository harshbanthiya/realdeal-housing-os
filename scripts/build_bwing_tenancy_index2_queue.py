#!/usr/bin/env python3
"""Phase 6.24 — B-Wing 3BHK-for-rent shortlist + Index II doc-search queue.

Reads the operator's IGR eSearch ".xls" result exports (HTML tables, UTF-16) directly
and isolates Kalpataru Radiance **B-Wing (Brilliance) Leave & License (tenancy)**
registrations from the **last two years**. The result list lacks BHK / PAN / carpet
area / monthly rent / licence period for the *English-structured* rows — those need
Index II — but the *Marathi-structured* rows frequently DO carry rent + period +
deposit inline, which we mine here and use to compute a lease-expiry estimate.

Output (git-ignored under exports/igr_bwing_tenancy/):
  * bwing_tenancy_index2_queue.csv  — same schema as the main doc-search queue, so
    the operator can run the IGR "Document Number" search (District/SRO/Year/Doc) and
    download Index II for each. PAN + licence duration + carpet area (→ confirm 3BHK)
    come from those Index II PDFs.
  * BWING_TENANCY_SHORTLIST.md       — human-readable shortlist incl. inline rent/expiry.

NO scrape / IGR / external call — local files only. Read-only (writes only to exports/).
Wing detection recovers rows the society-name parser misses by reading the embedded
flat prefix (`B-224`, `B Wing`, `Tower B`). Requires: indic-transliteration (via helpers).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
PROJECT_ROOT = SCRIPTS.parent
OUT_DIR = PROJECT_ROOT / "exports" / "igr_bwing_tenancy"

from parse_igr_xls_exports import load, tcells, classify  # noqa: E402
from parse_igr_results_to_staging import (  # noqa: E402
    parse_property as lprop, classify_doctype, detect_wing,
)

COLS = ["srocode", "internaldocumentnumber", "docno", "docname", "registrationdate", "sroname",
        "sellerparty", "purchaserparty", "propertydescription", "areaname",
        "consideration_amt", "marketvalue", "dateofexecution", "stampdutypaid", "registrationfees", "status"]
DISTRICT = "Mumbai Suburban"
REG_TYPE = "eRegistration"
REG_TYPE_FALLBACK = "Regular / iSarita 2.0"
RECENT_YEARS = {"2024", "2025", "2026"}


def is_bwing(desc: str) -> bool:
    if detect_wing(desc) == "Wing B-Brilliance":
        return True
    flat = (lprop(desc).get("flat") or "")
    if re.match(r"\s*B[-\s]?\d", flat, re.I):
        return True
    return bool(re.search(r"\bB[-\s]?wing\b|ब\s*िवंग|ब\s*विंग|wing\s*[-:]?\s*B\b|टॉवर\s*ब\b|tower\s*B\b", desc, re.I))


def clean_flat(desc: str) -> str | None:
    """Flat token after 'Flat No:' (EN) or 'सदनिका क्रं.' (MR), wing words stripped, B- kept."""
    m = re.search(r"Flat No:\s*(.*?)\s*(?:Shop No:|Floor No:|,|$)", desc, re.I)
    raw = m.group(1) if m else None
    if not raw:
        m = re.search(r"सदनिका\s*(?:क्रं|क्र|नं)\.?\s*([0-9][0-9A-Za-z\-/ ]*)", desc)
        raw = m.group(1) if m else None
    if not raw:
        raw = lprop(desc).get("flat")
    if not raw:
        return None
    raw = re.sub(r"\b(B[-\s]?wing|wing\s*B|tower\s*B|Brilliance|ब\s*िवंग|टॉवर\s*ब)\b", "", raw, flags=re.I)
    num = re.search(r"([0-9][0-9A-Za-z]*)", raw)
    if not num:
        return None
    n = num.group(1)
    return f"B-{n}"


def clean_floor(desc: str) -> str | None:
    m = re.search(r"Floor No:\s*([0-9]+)", desc, re.I)
    if m:
        return m.group(1)
    m = re.search(r"([0-9]+)\s*(?:वा|व्या|था|ला)?\s*मजल", desc)
    return m.group(1) if m else None


def parse_inline_terms(desc: str) -> dict:
    """Marathi result-list rows often embed rent/deposit/period. English ones don't."""
    out = {"rent": None, "deposit": None, "tenure_months": None}
    rents = re.findall(r"मासिक\s*भाडे\s*(?:रु\.?|रू\.?)?\s*([0-9,]+)", desc)
    if rents:
        out["rent"] = max(int(r.replace(",", "")) for r in rents)  # highest (escalated) slab
    m = re.search(r"अनामत(?:\s*रक्[कमी]+)?\s*(?:रु\.?|रू\.?)?\s*([0-9,]+)", desc)
    if m:
        out["deposit"] = int(m.group(1).replace(",", ""))
    m = re.search(r"कालावधी\s*([0-9]+)\s*मिहन्|कालावधी\s*([0-9]+)\s*महिन", desc)
    if m:
        out["tenure_months"] = int(m.group(1) or m.group(2))
    return out


def iso(d: str | None) -> str | None:
    if not d:
        return None
    m = re.search(r"([0-3]?\d)[/\-]([01]?\d)[/\-](\d{4})", d)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def add_months(d: str, months: int) -> str:
    y, mo, da = (int(x) for x in d.split("-"))
    mo2 = mo - 1 + months
    y2, mo2 = y + mo2 // 12, mo2 % 12 + 1
    da2 = min(da, [31, 29 if y2 % 4 == 0 and (y2 % 100 != 0 or y2 % 400 == 0) else 28,
                   31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo2 - 1])
    return f"{y2:04d}-{mo2:02d}-{da2:02d}"


def main() -> int:
    ap = argparse.ArgumentParser(description="B-Wing tenancy -> Index II doc-search queue (read-only).")
    ap.add_argument("--xls-dir", default=str(Path.home() / "Downloads"))
    ap.add_argument("--glob", default="SearchResult*.xls")
    args = ap.parse_args()

    files = sorted(Path(args.xls_dir).glob(args.glob))
    if not files:
        print(f"No files matching {args.glob} in {args.xls_dir}")
        return 1

    seen: set = set()
    rows: list[dict] = []
    for f in files:
        trs = re.findall(r"<tr[^>]*>(.*?)</tr>", load(f), re.S)
        if len(trs) < 2:
            continue
        hdr = [h.lower() for h in tcells(trs[0])]
        H = {h: i for i, h in enumerate(hdr)}
        if "propertydescription" not in H or "docno" not in H:
            continue
        get = lambda c, k: c[H[k]] if k in H and H[k] < len(c) else ""
        for r in trs[1:]:
            c = tcells(r)
            if len(c) <= H["propertydescription"]:
                continue
            uid = get(c, "internaldocumentnumber") or f"{get(c,'srocode')}|{get(c,'docno')}|{get(c,'registrationdate')[-4:]}"
            if uid in seen:
                continue
            seen.add(uid)
            rec = {k: get(c, k) for k in COLS}
            desc = rec["propertydescription"]
            yr = rec["registrationdate"][-4:]
            _et, cat = classify_doctype(rec["docname"])
            if cat == "tenancy" and yr in RECENT_YEARS and classify(desc) == "kalpataru" and is_bwing(desc):
                rows.append(rec)

    # build queue rows
    out_rows: list[dict] = []
    flat_counts: dict[str, int] = {}
    for r in rows:
        fk = clean_flat(r["propertydescription"])
        if fk:
            flat_counts[fk] = flat_counts.get(fk, 0) + 1
    for r in sorted(rows, key=lambda x: (x["registrationdate"][-4:], x["docno"])):
        desc = r["propertydescription"]
        flat = clean_flat(desc)
        floor = clean_floor(desc)
        # B/C/D carry 6 units/floor: flat NNu -> floor NN. Flag rows whose label disagrees
        # with the stated floor (usually the "Shop No:"-style rows with odd flat fields).
        unit_digits = re.sub(r"\D", "", flat or "")
        derived_floor = str(int(unit_digits) // 10) if unit_digits and len(unit_digits) >= 2 else ""
        flat_floor_ok = "yes" if (derived_floor and floor and derived_floor == floor) else (
            "verify" if (floor and derived_floor) else "")
        rdate = iso(r["registrationdate"])
        edate = iso(r["dateofexecution"]) or rdate
        terms = parse_inline_terms(desc)
        expiry = add_months(edate, terms["tenure_months"]) if (edate and terms["tenure_months"]) else None
        active = (expiry >= date.today().isoformat()) if expiry else None
        has_inline = bool(terms["rent"] or terms["tenure_months"])
        out_rows.append({
            "priority": 1,
            "status": "has_inline_terms" if has_inline else "needs_index22_tenancy",
            "apartment_key": flat or "",
            "wing": "B",
            "unit_number": (flat or "").replace("B-", ""),
            "category": "tenancy",
            "document_type": "leave_and_license",
            "doc_number": r["docno"],
            "registration_year": r["registrationdate"][-4:],
            "registration_date": rdate or "",
            "date_of_execution": edate or "",
            "district": DISTRICT,
            "sro_code": r["srocode"],
            "sro_office": r["sroname"],
            "registration_type_primary": REG_TYPE,
            "registration_type_fallback": REG_TYPE_FALLBACK,
            "floor": floor or "",
            "flat_floor_check": flat_floor_ok,
            "relet_count_2yr": flat_counts.get(flat or "", 1),
            "inline_monthly_rent": terms["rent"] or "",
            "inline_deposit": terms["deposit"] or (r["consideration_amt"] or ""),
            "inline_tenure_months": terms["tenure_months"] or "",
            "lease_expiry_est": expiry or "",
            "lease_active_est": "" if active is None else ("yes" if active else "expired"),
            "has_index22_pdf": False,
            "search_instruction": (
                f"Doc Search -> {REG_TYPE}; District {DISTRICT}; SRO {r['sroname']} (code {r['srocode']}); "
                f"Year {r['registrationdate'][-4:]}; Doc.No. {r['docno']}; solve CAPTCHA; open IndexII "
                f"(read PAN, monthly rent, licence period, carpet area -> confirm 3BHK)."),
            "property_description_raw": re.sub(r"\s+", " ", desc).strip(),
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "bwing_tenancy_index2_queue.csv"
    fields = list(out_rows[0].keys()) if out_rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    # markdown shortlist
    md = ["# B-Wing (Brilliance) — Leave & License shortlist (last 2 years)", "",
          f"Source: {len(files)} IGR .xls exports · {len(out_rows)} B-Wing tenancy registrations · "
          "Kalpataru Radiance, CTS 260/5A, Goregaon West.", "",
          "BHK / PAN / carpet area / licence period come from **Index II** (queue CSV). "
          "Rent/period shown below are inline from the result list where the row was Marathi-formatted.", "",
          "| Doc / Year | Reg date | SRO | Flat | Floor | Flat✓ | Re-let | Inline rent | Term | Est. expiry | Active? |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for o in out_rows:
        md.append(f"| {o['doc_number']}/{o['registration_year']} | {o['registration_date']} | "
                  f"{o['sro_code']} | {o['apartment_key']} | {o['floor']} | "
                  f"{o['flat_floor_check'] or '—'} | "
                  f"{('×'+str(o['relet_count_2yr'])) if o['relet_count_2yr'] > 1 else '—'} | "
                  f"{('₹'+format(int(o['inline_monthly_rent']),',')) if o['inline_monthly_rent'] else '—'} | "
                  f"{(str(o['inline_tenure_months'])+'mo') if o['inline_tenure_months'] else '—'} | "
                  f"{o['lease_expiry_est'] or '—'} | {o['lease_active_est'] or '—'} |")
    md += ["", "## How to fetch Index II",
           f"For each doc: IGR eSearch → **{REG_TYPE}** → District **{DISTRICT}** → select **SRO** (per row) → "
           f"**Year** → enter **Doc.No.** → solve CAPTCHA → open **IndexII**. Save PDF; the parser then reads "
           "PAN, monthly rent, licence period (→ expiry), and carpet area (→ confirm 3BHK)."]
    md_path = OUT_DIR / "BWING_TENANCY_SHORTLIST.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    inline = sum(1 for o in out_rows if o["status"] == "has_inline_terms")
    print(f"Parsed {len(files)} files -> {len(seen)} unique rows -> {len(out_rows)} B-Wing tenancy (last 2 yrs).")
    print(f"  with inline rent/term already: {inline}   need Index II: {len(out_rows) - inline}")
    active = [o for o in out_rows if o["lease_active_est"] == "yes"]
    print(f"  leases estimated still ACTIVE (from inline term): {len(active)}")
    print(f"\nCSV:      {csv_path}")
    print(f"Shortlist: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
