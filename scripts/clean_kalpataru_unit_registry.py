#!/usr/bin/env python3
"""Phase 6.24 — rebuild the canonical Kalpataru Radiance unit grid + re-link registrations.

The canonical "Kalpataru Radiance" building accumulated add-only units from the IGR .xls
loader, inflating each physical flat into several rows under different flat-number encodings
(`1203` == `123` == floor 12 / position 3). This reconciles to ONE unit per (tower, floor,
position) on the operator-confirmed grid:

    Wing A = 5 apartments/floor, Wings B/C/D = 6/floor, floors 1..N (N derived from data),
    Wing E = shops (handled separately; off-grid).

For each grid cell it keeps ONE unit (preferring the original base `(none)`-source row, then
the oldest), re-points every registration / relationship / match / review FK from the
duplicates onto the keeper, deactivates the duplicates, and creates any missing cell so the
registry shows the full stack. Units that don't map to a valid cell (shops, podium, bad
parses) are left active but flagged `metadata.offgrid=true` and reported — never destroyed.

Reversible: deactivations set canonical_status='superseded_6_24' + metadata.superseded_by;
re-pointed rows stamp raw_context/metadata.prior_building_unit_id; created rows tag
metadata.cleanup_phase='6.24'. `--revert` undoes all of it.

Dry-run by default. Writing requires --apply AND --real-ok. NO external/IGR/scrape calls.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / "docker" / ".env"
BUILDING = "Kalpataru Radiance"
PHASE = "6.24"
SUPERSEDED = "duplicate"                          # canonical_status CHECK allows only active/inactive/duplicate/needs_review
MERGE_MARK = "6.24_merge"                          # metadata.cleanup_phase marker -> revert targets only our merges
PER_FLOOR = {"A": 5, "B": 6, "C": 6, "D": 6}      # E = shops (off-grid)
MAX_FLOOR = 31                                    # per building_tower_structure: all towers 31 floors
# FK tables that point at building_units.id (must be re-pointed before a unit is deactivated).
FK_TABLES = ["unit_registration_records", "contact_property_relationships",
             "registration_party_contact_matches", "property_relationship_review_items"]


def env(key: str) -> str:
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1]
    return ""


def psql(sql: str) -> tuple[int, str]:
    u, p, d = env("POSTGRES_USER"), env("POSTGRES_PASSWORD"), env("POSTGRES_DB")
    if not (u and p and d):
        return 1, "Missing POSTGRES_* in docker/.env."
    cmd = ["docker", "exec", "-i", "-e", f"PGPASSWORD={p}", "realdeal-postgres", "psql",
           "-U", u, "-d", d, "-v", "ON_ERROR_STOP=1", "-At", "-F", "|"]
    r = subprocess.run(cmd, input=sql, text=True, capture_output=True, check=False)
    return r.returncode, (r.stderr.strip() or r.stdout.strip()) if r.returncode else (r.stdout.strip() or r.stderr.strip())


def tower_of(wing: str) -> str:
    m = re.search(r"([A-Za-z])\s*$", wing or "")
    return m.group(1).upper() if m else ""


def derive_cell(unit: str, per_floor: int) -> tuple[int, int] | None:
    """flat-number string -> (floor, pos) for this tower, or None (off-grid).

    Flat numbers mix two encodings that collide at 3-4 digits:
      floor*10+pos  ->  `224` = floor 22 / pos 4
      floor*100+pos ->  `803` = floor 8 / pos 03,  `1504` = floor 15 / pos 04
    We try both per length and accept the FIRST that lands in a real cell
    (1..MAX_FLOOR floors, 1..per_floor positions), which disambiguates them."""
    d = re.sub(r"\D", "", str(unit))
    if len(d) < 2:
        return None
    n = int(d)
    if len(d) == 2:
        cands = [(n // 10, n % 10)]
    elif len(d) == 3:
        cands = [(n // 10, n % 10), (n // 100, n % 100)]
    else:  # 4+
        cands = [(n // 100, n % 100), (n // 1000, n % 1000)]
    for fl, pos in cands:
        if 1 <= fl <= MAX_FLOOR and 1 <= pos <= per_floor:
            return fl, pos
    return None


def q(v) -> str:
    return "NULL" if v in (None, "") else "'" + str(v).replace("'", "''") + "'"


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebuild canonical Kalpataru unit grid (dry-run default).")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--real-ok", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    code, bid = psql(f"select id from buildings where name={q(BUILDING)} order by created_at limit 1;")
    if code or not bid:
        print(f"Refusing: building {BUILDING!r} not found."); return 1
    bid = bid.splitlines()[0]

    if args.revert:
        if not (args.apply and args.real_ok):
            _, n = psql(f"select count(*) from building_units where building_id='{bid}' and metadata->>'cleanup_phase'='{MERGE_MARK}';")
            _, c = psql(f"select count(*) from building_units where building_id='{bid}' and metadata->>'cleanup_phase'='{PHASE}';")
            print(f"Revert dry-run: would reactivate {n} superseded units, delete {c} created grid cells, "
                  "and restore re-pointed FKs from prior_building_unit_id."); return 0
        sql = ["BEGIN;"]
        for t in FK_TABLES:
            sql.append(f"UPDATE {t} SET building_unit_id=(raw_context->>'prior_building_unit_id')::uuid "
                       f"WHERE raw_context->>'cleanup_phase_6_24'='moved';")
        sql.append(f"DELETE FROM building_units WHERE building_id='{bid}' AND metadata->>'cleanup_phase'='{PHASE}';")
        sql.append(f"UPDATE building_units SET canonical_status='active' WHERE building_id='{bid}' AND metadata->>'cleanup_phase'='{MERGE_MARK}';")
        sql.append("COMMIT;")
        c, out = psql("\n".join(sql))
        print(("Revert failed:\n" + out) if c else "Reverted Phase 6.24 registry cleanup."); return c

    # pull all active canonical units with FK counts + source + age
    cnt_expr = " + ".join(f"(select count(*) from {t} x where x.building_unit_id=bu.id)" for t in FK_TABLES)
    _, rows = psql(
        f"select bu.id, coalesce(bu.wing,''), coalesce(bu.unit_number,''), coalesce(bu.metadata->>'source','(none)'), "
        f"extract(epoch from bu.created_at)::bigint, ({cnt_expr}) "
        f"from building_units bu where bu.building_id='{bid}' and bu.canonical_status='active';")
    units = []
    for ln in rows.splitlines():
        uid, wing, unum, src, created, fk = (ln.split("|") + [""] * 6)[:6]
        units.append({"id": uid, "wing": wing, "unit": unum, "src": src,
                      "created": int(created or 0), "fk": int(fk or 0), "tower": tower_of(wing)})

    cells: dict[tuple, list] = defaultdict(list)   # (tower,floor,pos) -> units
    offgrid: list = []
    for u in units:
        cell = derive_cell(u["unit"], PER_FLOOR[u["tower"]]) if u["tower"] in PER_FLOOR else None
        if cell:
            cells[(u["tower"], cell[0], cell[1])].append(u)
        else:
            offgrid.append(u)

    # keeper = base (none) source first, then most FKs, then oldest
    def keyfn(u):
        return (0 if u["src"] == "(none)" else 1, -u["fk"], u["created"])
    merges = []   # (keeper, [dupes])
    for cell, us in cells.items():
        us = sorted(us, key=keyfn)
        if len(us) > 1:
            merges.append((cell, us[0], us[1:]))

    max_floor = {t: 0 for t in PER_FLOOR}
    for (t, fl, pos) in cells:
        max_floor[t] = max(max_floor[t], fl)
    # Authoritative grid (building_tower_structure): every tower = 31 floors.
    missing = []
    for t in PER_FLOOR:
        for fl in range(1, MAX_FLOOR + 1):
            for pos in range(1, PER_FLOOR[t] + 1):
                if (t, fl, pos) not in cells:
                    missing.append((t, fl, pos))

    dup_units = sum(len(d) for _, _, d in merges)
    fk_to_move = sum(u["fk"] for _, _, d in merges for u in d)
    print(f"Building '{BUILDING}' ({bid})")
    print(f"  active units now: {len(units)}   off-grid (shops/podium/bad, kept+flagged): {len(offgrid)}")
    print(f"  grid cells occupied: {len(cells)}   cells with duplicates: {len(merges)}")
    print(f"  duplicate units to deactivate: {dup_units}   FK rows to re-point: {fk_to_move}")
    print(f"  max floor per tower: {max_floor}")
    print(f"  missing grid cells to create: {len(missing)}")
    per_tower = {t: sum(1 for (tt, _, _) in cells if tt == t) + sum(1 for (tt, _, _) in missing if tt == t) for t in PER_FLOOR}
    print(f"  resulting unit count per tower (A=5/fl, B/C/D=6/fl): {per_tower}  total={sum(per_tower.values())}")
    if offgrid[:8]:
        print("  sample off-grid: " + ", ".join(f"{u['wing'].strip()[-1:]}-{u['unit']}" for u in offgrid[:8]))

    if not (args.apply and args.real_ok):
        print("\nDry run only — NO DB writes. To execute: --apply --real-ok  (reverse with --revert --apply --real-ok)")
        return 0

    # ---- apply ----
    BATCH = 40
    stmts = ["BEGIN;"]
    for cell, keep, dupes in merges:
        for d in dupes:
            for t in FK_TABLES:
                stmts.append(
                    f"UPDATE {t} SET building_unit_id='{keep['id']}', "
                    f"raw_context=coalesce(raw_context,'{{}}'::jsonb) || jsonb_build_object("
                    f"'prior_building_unit_id','{d['id']}','cleanup_phase_6_24','moved') "
                    f"WHERE building_unit_id='{d['id']}';")
            stmts.append(
                f"UPDATE building_units SET canonical_status='{SUPERSEDED}', "
                f"metadata=coalesce(metadata,'{{}}'::jsonb) || jsonb_build_object("
                f"'superseded_by','{keep['id']}','cleanup_phase','{MERGE_MARK}') WHERE id='{d['id']}';")
    for i, (t, fl, pos) in enumerate(missing):
        unum = f"{fl}{pos}"
        wlabel = next((u["wing"] for u in units if u["tower"] == t and u["wing"]), f"KALPATARU RADIANCE  {t}")
        tag = {"source": "grid_rebuild_6_24", "cleanup_phase": PHASE, "tower": t, "floor": fl, "pos": pos, "is_fake": False}
        stmts.append(
            f"INSERT INTO building_units (building_id, building_name, wing, unit_number, floor, canonical_status, metadata) "
            f"VALUES ('{bid}', {q(BUILDING)}, {q(wlabel)}, {q(unum)}, {fl}, 'active', "
            f"'{json.dumps(tag)}'::jsonb);")
        if i % BATCH == BATCH - 1:
            stmts.append("COMMIT;"); c, out = psql("\n".join(stmts))
            if c:
                print("Apply failed (insert batch):\n" + out); return c
            stmts = ["BEGIN;"]
    for u in offgrid:
        stmts.append(f"UPDATE building_units SET metadata=coalesce(metadata,'{{}}'::jsonb) || "
                     f"jsonb_build_object('offgrid',true,'cleanup_phase','{PHASE}_offgrid') WHERE id='{u['id']}';")
    stmts.append("COMMIT;")
    c, out = psql("\n".join(stmts))
    if c:
        print("Apply failed:\n" + out); return c
    _, after = psql(
        f"select coalesce(wing,''), count(*) from building_units where building_id='{bid}' "
        f"and canonical_status='active' group by 1 order by 1;")
    print("Applied. Active units per wing now:\n" + after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
