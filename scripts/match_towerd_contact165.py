#!/usr/bin/env python3
"""Attach Contact_List_165 phones to Imperial Heights Tower D (wing D) names.

Tower D resident names were loaded from MyGate screenshots (IMG_1381-1487).
Contact_List_165_Updated.xlsx holds name->phone for those same residents, but the
spellings differ (MyGate "DR MONICA JACOB" vs list "Monica Jacob"), so this uses
the tested fuzzy matcher from consolidate_towerd_mygate.best_phone_match.

    python3 scripts/match_towerd_contact165.py            # dry-run, threshold sweep
    python3 scripts/match_towerd_contact165.py --apply --min 0.85
    python3 scripts/match_towerd_contact165.py --demo
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "scripts"))
from consolidate_towerd_mygate import best_phone_match, norm_name  # noqa: E402
from extract_building_contacts import norm_phone  # noqa: E402
from _db import run_psql, sql_literal as lit  # noqa: E402

XLSX = "/Users/sheeed/Downloads/Contact_List_165_Updated.xlsx"
BATCH = "towerd_contact165_20260710"


def load_c165():
    import openpyxl
    ws = openpyxl.load_workbook(XLSX, read_only=True, data_only=True).active
    out = []
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if not r or not r[1] or len(r) < 3 or not r[2]:
            continue
        e164, _ = norm_phone(str(r[2]))
        if e164:
            out.append({"name": str(r[1]).strip(), "phone": e164})
    return out


def load_targets():
    rc, out = run_psql("""
      select c.id, bu.unit_number, c.full_name from contact_property_relationships r
      join buildings b on b.id=r.building_id join contacts c on c.id=r.contact_id
      join building_units bu on bu.id=r.building_unit_id
      where b.name ilike '%imperial%' and bu.wing='D'
        and coalesce(nullif(c.phone_primary,''), c.whatsapp_number) is null;""")
    if rc:
        raise SystemExit(out)
    return [l.split("|") for l in out.splitlines() if "|" in l]


def match_all():
    c165 = load_c165()
    targets = load_targets()
    matches = []
    for cid, unit, name in targets:
        mname, phone, score = best_phone_match(name, c165)
        if phone:
            matches.append({"cid": cid, "unit": unit, "name": name,
                            "match": mname, "phone": phone, "score": score})
    return c165, targets, matches


def demo():
    c = [{"name": "Monica Jacob", "phone": "+919820011111"},
         {"name": "Pankaj Chaturvedi", "phone": "+919820022222"}]
    _, ph, sc = best_phone_match("DR MONICA JACOB", c)
    assert ph == "+919820011111" and sc >= 0.85, (ph, sc)
    _, ph2, sc2 = best_phone_match("Totally Different Person", c)
    assert sc2 < 0.85
    print("ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min", type=float, default=0.85)
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()

    c165, targets, matches = match_all()
    print(f"C165 phones: {len(c165)}   phone-less wing-D targets: {len(targets)}")
    for thr in (0.95, 0.9, 0.85, 0.8, 0.75):
        n = sum(1 for m in matches if m["score"] >= thr)
        print(f"  score >= {thr}: {n} matches")
    keep = [m for m in matches if m["score"] >= a.min]
    print(f"\n--- sample at min={a.min} ---")
    for m in sorted(keep, key=lambda x: -x["score"])[:8]:
        print(f"  {m['score']:.2f}  D-{m['unit']:<5} '{m['name'][:22]}' ~ '{m['match'][:20]}' -> {m['phone']}")
    for m in sorted(keep, key=lambda x: x["score"])[:6]:
        print(f"  {m['score']:.2f}  D-{m['unit']:<5} '{m['name'][:22]}' ~ '{m['match'][:20]}' -> {m['phone']}  (lowest kept)")

    if not a.apply:
        print(f"\nDRY-RUN: {len(keep)} would attach at min={a.min}. Re-run with --apply.")
        return
    stmts = []
    for m in keep:
        meta = json.dumps({"phone_source": "towerd_contact165", "score": m["score"],
                           "match_name": m["match"], "batch": BATCH})
        stmts.append(
            f"update contacts set phone_primary={lit(m['phone'])}, "
            f"whatsapp_number=coalesce(nullif(whatsapp_number,''),{lit(m['phone'])}), "
            f"metadata=coalesce(metadata,'{{}}'::jsonb)||{lit(meta)}::jsonb, updated_at=now() "
            f"where id={lit(m['cid'])} and coalesce(nullif(phone_primary,''),whatsapp_number) is null;")
    for i in range(0, len(stmts), 200):
        rc, out = run_psql("begin;\n" + "\n".join(stmts[i:i + 200]) + "\ncommit;")
        if rc:
            print("ERR", out[:200]); return
    print(f"DONE: attached {len(keep)} phones (batch {BATCH}). Reversible via metadata->>'batch'.")


if __name__ == "__main__":
    sys.exit(main())
