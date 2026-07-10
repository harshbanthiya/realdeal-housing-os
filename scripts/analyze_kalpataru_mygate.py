"""Dry analysis: how MyGate directory maps onto existing Kalpataru Radiance DB.

No writes. Prints: unit match/create counts per wing, and name overlap vs
existing contacts. Informs load_kalpataru_mygate.py before any commit.
"""
import json
import re
from pathlib import Path

from _db import run_psql

BUILDING_ID = "f63d75ab-2ef9-48a9-afe2-cab3c4283283"
DUMP = Path(__file__).resolve().parents[1] / "captures" / "mygate_directory"


def norm_name(n: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", (n or "").lower())).strip()


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def load_mygate():
    """-> list of (wing_letter, flat_digits, rtypename, rname, r_user_id)."""
    out = []
    for f in sorted(DUMP.glob("building_*.json")):
        d = json.loads(f.read_text())
        w = d["buildingname"].strip()
        if w not in ("A", "B", "C", "D"):
            continue
        for flat in d.get("flats") or []:
            fd = digits(flat["fname"])
            if not fd:
                continue
            for r in flat.get("residents") or []:
                out.append((w, fd, r["rtypename"], r["rname"], r["r_user_id"]))
    return out


def main():
    mg = load_mygate()
    print(f"MyGate residents parsed: {len(mg)}")

    # existing units: wing letter + digit key
    _, out = run_psql(f"""
        SELECT regexp_replace(upper(wing),'.*([A-Z])\\s*$','\\1') AS w,
               regexp_replace(unit_number,'\\D','','g') AS d, count(*)
        FROM building_units
        WHERE building_id='{BUILDING_ID}'
        GROUP BY 1,2;""")
    existing = {}
    for line in out.strip().splitlines():
        p = [x.strip() for x in line.split("|")]
        if len(p) == 3 and p[1]:
            existing[(p[0], p[1])] = int(p[2])

    mg_units = {(w, d) for w, d, *_ in mg}
    matched = {u for u in mg_units if u in existing}
    tocreate = mg_units - matched
    print(f"\nDistinct MyGate units: {len(mg_units)}")
    print(f"  match existing DB unit: {len(matched)}")
    print(f"  need CREATE (occupied, DB lacked): {len(tocreate)}")
    for w in "ABCD":
        m = sum(1 for (ww, _) in matched if ww == w)
        c = sum(1 for (ww, _) in tocreate if ww == w)
        print(f"    wing {w}: {m} matched, {c} to create")

    # name overlap vs existing contacts (global + kalpataru-scoped)
    mg_names = {norm_name(n) for _, _, _, n, _ in mg}
    _, out = run_psql("""
        SELECT DISTINCT lower(regexp_replace(full_name,'[^a-zA-Z ]',' ','g')) FROM contacts;""")
    all_norm = {re.sub(r"\s+", " ", x).strip() for x in out.strip().splitlines()}
    _, out = run_psql(f"""
        SELECT DISTINCT lower(regexp_replace(c.full_name,'[^a-zA-Z ]',' ','g'))
        FROM contacts c
        JOIN contact_property_relationships r ON r.contact_id=c.id
        JOIN building_units bu ON bu.id=r.building_unit_id
        WHERE bu.building_id='{BUILDING_ID}';""")
    kalp_norm = {re.sub(r"\s+", " ", x).strip() for x in out.strip().splitlines()}
    print(f"\nDistinct MyGate names: {len(mg_names)}")
    print(f"  also an existing contact (any building): {len(mg_names & all_norm)}")
    print(f"  also a Kalpataru-linked contact: {len(mg_names & kalp_norm)}")


if __name__ == "__main__":
    main()
