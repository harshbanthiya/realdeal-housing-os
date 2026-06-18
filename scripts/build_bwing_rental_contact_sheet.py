#!/usr/bin/env python3
"""Phase 6.29 — B-Wing rental outreach sheet: cross-reference tenancy flats with RDH contact files.

The client wants to rent in B-Wing (Brilliance). We have (a) the IGR tenancy registrations per flat
(who's the landlord/tenant, last rent, lease expiry) and (b) RDH's own owner/tenant contact files
(name + phone, keyed by the "OKR <wing> <flat> <name>" naming convention). This joins them BY FLAT
NUMBER so each B-Wing flat gets reachable phone numbers attached.

Contact sources (RDH DATA 2024) are auto-discovered by Kalpataru-ish filename. Extracts every
O?KRI? <wing> <flat> <name> + phone, plus the secondary (flat,name,phone) columns in the owners
sheet. Phones normalised to 10-digit Indian mobiles (intl kept with +). Output: a client-ready
markdown doc + a CSV, under exports/bwing_rental/ (git-ignored).

Read-only on the data folder; queries local Postgres for registration names. NO external calls.
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
PROJECT_ROOT = SCRIPTS.parent
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
OUT_DIR = PROJECT_ROOT / "exports" / "bwing_rental"
TENANCY_CSV = PROJECT_ROOT / "exports" / "igr_tenancy" / "tenancy_index2_queue.csv"
DATA_ROOT = Path("/Volumes/RDH 5TB/RDH DATA 2024")
BUILDING_ID = "f63d75ab-2ef9-48a9-afe2-cab3c4283283"

# O[K]R[I] <wing A-E> <flat 1-4 digits> <name...>
OKR_RE = re.compile(r"\bO?KRI?\s+([A-Ea-e])\s+(\d{1,4})\s+(.+)$", re.I)


def env(key: str) -> str:
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1]
    return ""


def psql(sql: str) -> str:
    u, p, d = env("POSTGRES_USER"), env("POSTGRES_PASSWORD"), env("POSTGRES_DB")
    r = subprocess.run(["docker", "exec", "-i", "-e", f"PGPASSWORD={p}", "realdeal-postgres", "psql",
                        "-U", u, "-d", d, "-At", "-F", "|", "-c", sql], capture_output=True, text=True)
    return r.stdout


def norm_phone(raw: str) -> str | None:
    s = str(raw or "").strip()
    intl = s.startswith("+") and not s.startswith("+91")
    d = re.sub(r"\D", "", s)
    if not d:
        return None
    if intl and len(d) >= 9:
        return "+" + d
    if d.startswith("91") and len(d) >= 12:
        d = d[2:12]
    elif len(d) > 10 and d[-10:][0] in "6789":
        d = d[-10:]
    if len(d) == 10 and d[0] in "6789":
        return d
    return None  # landline / malformed -> drop


def clean_name(nm: str) -> str:
    nm = re.sub(r"kalpataru\s+radiance|radiance", "", nm, flags=re.I)
    return re.sub(r"\s+", " ", nm).strip(" -,")


def discover_files() -> list[Path]:
    pats = ("kalpataru", "kalptaru", "okr", "owners", "tenant", "tentant", "radiance", "owners_tenants")
    out = []
    for p in DATA_ROOT.rglob("*"):
        if p.name.startswith("._") or not p.is_file():
            continue
        if p.suffix.lower() not in (".csv", ".xlsx", ".xls"):
            continue
        if any(k in p.name.lower() for k in pats):
            out.append(p)
    return sorted(out)


def rows_of(path: Path):
    """Yield list-of-cells rows from csv/xlsx."""
    if path.suffix.lower() == ".csv":
        try:
            with path.open(encoding="utf-8", errors="replace", newline="") as fh:
                for r in csv.reader(fh):
                    yield r
        except Exception:  # noqa: BLE001
            return
    else:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            for ws in wb.worksheets:
                for r in ws.iter_rows(values_only=True):
                    yield [("" if c is None else str(c)) for c in r]
        except Exception:  # noqa: BLE001
            return


def extract(files: list[Path]) -> dict[str, list[dict]]:
    """flat_key 'B-224' -> [{name, phone, source, role_hint}]"""
    by_flat: dict[str, list[dict]] = defaultdict(list)
    seen: set = set()
    for f in files:
        src = f.name
        role_hint = "tenant" if re.search(r"tenant|tentant", src, re.I) else "owner"
        for row in rows_of(f):
            cells = [str(c).strip() for c in row]
            joined = " | ".join(cells)
            # all OKR-pattern hits in the row (name cell), with a phone from the row
            for ci, cell in enumerate(cells):
                m = OKR_RE.search(cell)
                if not m:
                    continue
                wing, flat, name = m.group(1).upper(), m.group(2), clean_name(m.group(3))
                # phone: scan other cells, prefer the immediate neighbours
                order = [ci - 1, ci + 1] + [j for j in range(len(cells)) if j not in (ci, ci - 1, ci + 1)]
                phone = next((norm_phone(cells[j]) for j in order if 0 <= j < len(cells) and norm_phone(cells[j])), None)
                key = f"{wing}-{flat}"
                dedup = (key, name.lower(), phone)
                if phone and dedup not in seen:
                    seen.add(dedup)
                    by_flat[key].append({"name": name, "phone": phone, "source": src, "role": role_hint})
            # secondary columns in the owners sheet: trailing "<flat>,<name>,<phone>" (wing inferred B-only file)
            if "owners data" in src.lower():
                m2 = re.search(r"(?<![0-9])(\d{1,4})\s*\|\s*([A-Za-z][A-Za-z. ]{3,40})\s*\|\s*([0-9+][0-9 ]{7,})", joined)
                if m2:
                    flat, name, ph = m2.group(1), clean_name(m2.group(2)), norm_phone(m2.group(3))
                    key = f"B-{flat}"
                    dedup = (key, name.lower(), ph)
                    if ph and dedup not in seen:
                        seen.add(dedup)
                        by_flat[key].append({"name": name, "phone": ph, "source": src + " (2nd col)", "role": "owner"})
    return by_flat


def reg_bwing() -> dict[str, dict]:
    """flat unit_number -> {lessors:set, lessees:set} from IGR tenancy registrations (B-wing)."""
    out: dict[str, dict] = defaultdict(lambda: {"lessor": set(), "lessee": set()})
    rows = psql(
        "select bu.unit_number, p.party_role, coalesce(p.party_name_english,p.party_name_normalized) "
        "from unit_registration_parties p join unit_registration_records r on r.id=p.unit_registration_record_id "
        "join building_units bu on bu.id=r.building_unit_id "
        f"where r.building_id='{BUILDING_ID}' and bu.wing ilike '%B' and r.transaction_category='tenancy';")
    for ln in rows.splitlines():
        unum, role, name = (ln.split("|") + ["", "", ""])[:3]
        if role in ("lessor", "lessee") and name:
            out[unum][role].add(name.strip())
    return out


def main() -> int:
    if not TENANCY_CSV.exists():
        print(f"Missing {TENANCY_CSV}; run build_tenancy_index2_queue.py first."); return 1
    tdata = {}
    for r in csv.DictReader(TENANCY_CSV.open()):
        if r["wing"] == "B" and r["apartment_key"]:
            num = re.sub(r"^B-", "", r["apartment_key"])
            cur = tdata.get(num)
            # keep the most recent tenancy row per flat
            if not cur or r["registration_date"] > cur["registration_date"]:
                tdata[num] = r

    files = discover_files()
    contacts = extract(files)
    reg = reg_bwing()

    # B-flat universe = flats with a B tenancy OR a B contact
    flats = sorted(set(tdata) | {k.split("-", 1)[1] for k in contacts if k.startswith("B-")},
                   key=lambda x: int(re.sub(r"\D", "", x) or 0))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_rows = []
    md = ["# B-Wing (Brilliance) — Rental Outreach Sheet", "",
          "Kalpataru Radiance, Goregaon West. Cross-references IGR tenancy registrations (who rents/owns each "
          "flat, last rent + lease expiry) with RDH owner/tenant contact files (name + phone, keyed by flat).",
          "", f"Contact sources scanned: {len(files)} files. Flats covered: {len(flats)}.", "",
          "**Priority calls** = flats with a recent/expiring lease AND a phone on file.", "",
          "| Flat | Floor | Landlord/Owner (reg) | Phone(s) on file | Contact name (file) | Last lease rent | Est. expiry | Current tenant (reg) |",
          "|---|---|---|---|---|---|---|---|"]
    priority = []
    for num in flats:
        key = f"B-{num}"
        t = tdata.get(num, {})
        rg = reg.get(num, {"lessor": set(), "lessee": set()})
        cs = contacts.get(key, [])
        phones = sorted({c["phone"] for c in cs})
        cnames = sorted({c["name"] for c in cs})
        landlord = "; ".join(sorted(rg["lessor"])[:2]) or "—"
        tenant = "; ".join(sorted(rg["lessee"])[:2]) or "—"
        rent = ("₹" + format(int(t["inline_monthly_rent"]), ",")) if t.get("inline_monthly_rent") else "—"
        expiry = t.get("lease_expiry_est") or "—"
        floor = t.get("floor") or ""
        row = {"flat": key, "floor": floor, "landlord_reg": landlord, "phones": ", ".join(phones),
               "contact_names": "; ".join(cnames), "last_rent": rent, "lease_expiry": expiry,
               "tenant_reg": tenant, "has_phone": bool(phones), "has_tenancy": bool(t)}
        csv_rows.append(row)
        line = (f"| {key} | {floor} | {landlord} | {', '.join(phones) or '—'} | {'; '.join(cnames) or '—'} | "
                f"{rent} | {expiry} | {tenant} |")
        if phones and t:
            priority.append(line)
        md.append(line)

    # priority section on top
    doc = md[:8] + ["", "## ⭐ Priority — recent/known lease + phone on file", "",
                    "| Flat | Floor | Landlord/Owner (reg) | Phone(s) | Contact name | Last rent | Est. expiry | Tenant |",
                    "|---|---|---|---|---|---|---|---|"] + (priority or ["| _none_ |"]) + ["", "## All B-Wing flats", ""] + md[8:]

    (OUT_DIR / "BWING_RENTAL_CONTACT_SHEET.md").write_text("\n".join(doc) + "\n", encoding="utf-8")
    with (OUT_DIR / "bwing_rental_contacts.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(csv_rows[0].keys()))
        w.writeheader(); w.writerows(csv_rows)

    withphone = sum(1 for r in csv_rows if r["has_phone"])
    print(f"Scanned {len(files)} contact files. B-Wing flats: {len(flats)}  with phone on file: {withphone}  "
          f"with tenancy reg: {sum(1 for r in csv_rows if r['has_tenancy'])}  priority (both): {len(priority)}")
    print("Doc: " + str(OUT_DIR / "BWING_RENTAL_CONTACT_SHEET.md"))
    print("CSV: " + str(OUT_DIR / "bwing_rental_contacts.csv"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
