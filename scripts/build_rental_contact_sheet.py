#!/usr/bin/env python3
"""Phase 6.30 — ALL-WINGS rental outreach sheet (generalises the B-Wing sheet to A/B/C/D/E).

Same join as build_bwing_rental_contact_sheet.py, across every wing: RDH owner/tenant contact files
("OKR <wing> <flat> <name>" + phone) cross-referenced BY FLAT with the IGR tenancy registrations
(landlord/tenant names, last rent, lease expiry). Emits one doc with a per-wing section + two CSVs
(per-flat and per-phone call list, each carrying a `wing` column) under exports/rental_all_wings/.

Read-only on the data folder; queries local Postgres for registration names. NO external calls.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
PROJECT_ROOT = SCRIPTS.parent
OUT_DIR = PROJECT_ROOT / "exports" / "rental_all_wings"
TENANCY_CSV = PROJECT_ROOT / "exports" / "igr_tenancy" / "tenancy_index2_queue.csv"

from build_bwing_rental_contact_sheet import (  # noqa: E402
    OKR_RE, norm_phone, clean_name, discover_files, rows_of, psql, BUILDING_ID,
)

WING_ORDER = ["A", "B", "C", "D", "E"]
WING_LABEL = {"A": "A — Ora", "B": "B — Brilliance", "C": "C — Allura", "D": "D — Lumina", "E": "E — Shops"}


def _nn(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def extract_all(files: list[Path]) -> dict[str, list[dict]]:
    """flat_key 'C-73' -> [{name, phone, source, role}] for every wing.

    Explicit 'OKR <wing> <flat>' entries are authoritative. The owners-sheet 2nd column has a flat +
    name + phone but NO wing (it's an independent list), so we resolve its wing by matching the
    person against the explicit entries (by flat+name, then by unique name); unresolved -> dropped."""
    okr_entries: list[dict] = []          # explicit, wing-tagged
    second: list[tuple] = []              # (flat, name, phone, src) wing-unknown
    for f in files:
        src = f.name
        role_hint = "tenant" if re.search(r"tenant|tentant", src, re.I) else "owner"
        for row in rows_of(f):
            cells = [str(c).strip() for c in row]
            for ci, cell in enumerate(cells):
                m = OKR_RE.search(cell)
                if not m:
                    continue
                wing, flat, name = m.group(1).upper(), m.group(2), clean_name(m.group(3))
                # phone is the name cell's immediate neighbour: prefer next (name,phone), then prev
                # (phone,name). Guard indices so col-0 OKR doesn't wrap to the row's LAST cell.
                order = [j for j in (ci + 1, ci - 1) if 0 <= j < len(cells)]
                phone = next((norm_phone(cells[j]) for j in order if norm_phone(cells[j])), None)
                if phone:
                    okr_entries.append({"wing": wing, "flat": flat, "name": name, "phone": phone,
                                        "source": src, "role": role_hint})
            if "owners data" in src.lower():
                m2 = re.search(r"(?<![0-9])(\d{1,4})\s*\|\s*([A-Za-z][A-Za-z. ]{3,40})\s*\|\s*([0-9+][0-9 ]{7,})",
                               " | ".join(cells))
                if m2:
                    ph = norm_phone(m2.group(3))
                    if ph:
                        second.append((m2.group(1), clean_name(m2.group(2)), ph, src + " (2nd col)"))

    # wing-resolution index from explicit entries
    flatname_wing: dict[tuple, str] = {}
    name_wings: dict[str, set] = defaultdict(set)
    for e in okr_entries:
        flatname_wing[(e["flat"], _nn(e["name"]))] = e["wing"]
        name_wings[_nn(e["name"])].add((e["wing"], e["flat"]))

    by_flat: dict[str, list[dict]] = defaultdict(list)
    seen: set = set()

    def add(wing, flat, name, phone, source, role):
        key = f"{wing}-{flat}"
        dedup = (key, name.lower(), phone)
        if dedup not in seen:
            seen.add(dedup)
            by_flat[key].append({"name": name, "phone": phone, "source": source, "role": role})

    for e in okr_entries:
        add(e["wing"], e["flat"], e["name"], e["phone"], e["source"], e["role"])
    for flat, name, phone, src in second:
        nn = _nn(name)
        wing = flatname_wing.get((flat, nn))
        if not wing:
            cands = {w for (w, fl) in name_wings.get(nn, ())}
            wing = next(iter(cands)) if len(cands) == 1 else None
        if wing:
            add(wing, flat, name, phone, src, "owner")
    return by_flat


def reg_all() -> dict[str, dict]:
    """(wing, unit_number) -> {lessor:set, lessee:set} from IGR tenancy registrations, all wings."""
    out: dict[str, dict] = defaultdict(lambda: {"lessor": set(), "lessee": set()})
    rows = psql(
        "select regexp_replace(upper(coalesce(bu.wing,'')), '.*([A-E])$', '\\1'), bu.unit_number, p.party_role, "
        "coalesce(p.party_name_english,p.party_name_normalized) "
        "from unit_registration_parties p join unit_registration_records r on r.id=p.unit_registration_record_id "
        "join building_units bu on bu.id=r.building_unit_id "
        f"where r.building_id='{BUILDING_ID}' and r.transaction_category='tenancy';")
    for ln in rows.splitlines():
        wing, unum, role, name = (ln.split("|") + ["", "", "", ""])[:4]
        if role in ("lessor", "lessee") and name and wing in WING_ORDER:
            out[f"{wing}-{unum}"][role].add(name.strip())
    return out


def main() -> int:
    if not TENANCY_CSV.exists():
        print(f"Missing {TENANCY_CSV}; run build_tenancy_index2_queue.py first."); return 1
    tdata: dict[str, dict] = {}
    for r in csv.DictReader(TENANCY_CSV.open()):
        if r["wing"] in WING_ORDER and r["apartment_key"]:
            num = re.sub(r"^[A-E]-", "", r["apartment_key"])
            key = f"{r['wing']}-{num}"
            if key not in tdata or r["registration_date"] > tdata[key]["registration_date"]:
                tdata[key] = r

    files = discover_files()
    contacts = extract_all(files)
    reg = reg_all()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    flat_rows, call_rows = [], []
    md = ["# Kalpataru Radiance — Rental Outreach Sheet (ALL WINGS)", "",
          "Cross-references IGR tenancy registrations (landlord/tenant, last rent, lease expiry) with RDH "
          "owner/tenant contact files (name + phone, keyed by flat). Grouped by wing.", "",
          f"Contact sources scanned: {len(files)} files.", ""]
    summary = []

    for wing in WING_ORDER:
        flats = sorted({k.split("-", 1)[1] for k in contacts if k.startswith(f"{wing}-")} |
                       {k.split("-", 1)[1] for k in tdata if k.startswith(f"{wing}-")},
                       key=lambda x: int(re.sub(r"\D", "", x) or 0))
        if not flats:
            continue
        wp = wt = 0
        section = [f"## Wing {WING_LABEL.get(wing, wing)}", "",
                   "| Flat | Floor | Landlord/Owner (reg) | Phone(s) on file | Contact name (file) | Last rent | Est. expiry | Tenant (reg) |",
                   "|---|---|---|---|---|---|---|---|"]
        pri = []
        for num in flats:
            key = f"{wing}-{num}"
            t = tdata.get(key, {})
            rg = reg.get(key, {"lessor": set(), "lessee": set()})
            cs = contacts.get(key, [])
            phones = sorted({c["phone"] for c in cs})
            cnames = sorted({c["name"] for c in cs})
            landlord = "; ".join(sorted(rg["lessor"])[:2]) or "—"
            tenant = "; ".join(sorted(rg["lessee"])[:2]) or "—"
            rent = ("₹" + format(int(t["inline_monthly_rent"]), ",")) if t.get("inline_monthly_rent") else "—"
            expiry = t.get("lease_expiry_est") or "—"
            floor = t.get("floor") or ""
            is_pri = bool(phones and t)
            wp += bool(phones); wt += bool(t)
            flat_rows.append({"priority": "yes" if is_pri else "", "wing": wing, "flat": key, "floor": floor,
                              "landlord_owner_reg": landlord, "phones": ", ".join(phones),
                              "contact_name_on_file": "; ".join(cnames), "last_rent": rent,
                              "lease_expiry_est": expiry, "current_tenant_reg": tenant,
                              "has_phone": "yes" if phones else "", "has_tenancy_reg": "yes" if t else ""})
            for c in cs:
                call_rows.append({"priority": "yes" if is_pri else "", "wing": wing, "flat": key, "floor": floor,
                                  "phone": c["phone"], "name_on_file": c["name"], "role_hint": c["role"],
                                  "landlord_owner_reg": landlord, "last_rent": rent, "lease_expiry_est": expiry,
                                  "source_file": c["source"]})
            line = (f"| {key} | {floor} | {landlord} | {', '.join(phones) or '—'} | {'; '.join(cnames) or '—'} | "
                    f"{rent} | {expiry} | {tenant} |")
            (pri if is_pri else section).append(line) if is_pri else section.append(line)
        # surface priority calls at the top of each wing section
        section = section[:1] + [f"_{len(flats)} flats · {wp} with phone · {wt} with tenancy reg · {len(pri)} priority_", ""] + \
            (["**⭐ Priority (recent lease + phone):**", "",
              "| Flat | Floor | Landlord/Owner | Phone(s) | Contact name | Last rent | Est. expiry | Tenant |",
              "|---|---|---|---|---|---|---|---|"] + pri + [""] if pri else []) + section[1:]
        md += section + [""]
        summary.append(f"{wing}: {len(flats)} flats, {wp} w/phone, {wt} tenancy, {len(pri)} priority")

    (OUT_DIR / "RENTAL_CONTACT_SHEET_ALL_WINGS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    wkey = {w: i for i, w in enumerate(WING_ORDER)}
    flat_first = sorted(flat_rows, key=lambda r: (r["priority"] != "yes", wkey.get(r["wing"], 9), int(re.sub(r"\D", "", r["flat"]) or 0)))
    with (OUT_DIR / "rental_contacts_all_wings.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(flat_first[0].keys())); w.writeheader(); w.writerows(flat_first)
    call_first = sorted(call_rows, key=lambda r: (r["priority"] != "yes", wkey.get(r["wing"], 9), int(re.sub(r"\D", "", r["flat"]) or 0), r["phone"]))
    with (OUT_DIR / "rental_call_list_all_wings.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(call_first[0].keys())); w.writeheader(); w.writerows(call_first)

    print(f"Scanned {len(files)} files. Per wing: " + " | ".join(summary))
    print(f"Totals: {len(flat_rows)} flats, {len(call_rows)} phone rows")
    print(f"Doc:           {OUT_DIR / 'RENTAL_CONTACT_SHEET_ALL_WINGS.md'}")
    print(f"Per-flat CSV:  {OUT_DIR / 'rental_contacts_all_wings.csv'}")
    print(f"Call-list CSV: {OUT_DIR / 'rental_call_list_all_wings.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
