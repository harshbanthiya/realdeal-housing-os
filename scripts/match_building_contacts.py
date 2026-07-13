#!/usr/bin/env python3
"""Attach phones to phone-less unit-registry names in IH + Kalpataru Radiance.

Targets = contacts linked to a unit whose phone is empty (~433 IH + ~2047 OKR).
Source = imports/screenshot_contacts/consolidated_contacts.csv (3.4k phones).

Matching is NAME-centric (unit numbering is inconsistent across sources) with
unit + building as corroboration. Only strong / probable matches ever attach;
anything ambiguous is written to a review file and left untouched.

Passes (best first):
  A strong  : name tokens overlap AND store unit-hint == target unit (wing+no)
  B strong  : full name token-set equal, all candidates share ONE phone
  C probable: >=2 shared name tokens, resolves to exactly ONE phone in-building
  ambiguous : >1 distinct phone and no unit tiebreak  -> review, not attached

    python3 scripts/match_building_contacts.py            # dry-run plan
    python3 scripts/match_building_contacts.py --apply     # write phones
    python3 scripts/match_building_contacts.py --demo
"""
from __future__ import annotations
import argparse, csv, json, re, sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
STORE = BASE / "imports/screenshot_contacts/consolidated_contacts.csv"
REVIEW = BASE / "imports/screenshot_contacts/match_review.csv"
BATCH = "building_contact_match_20260710"

HONOR = re.compile(r"\b(mr|mrs|ms|dr|smt|shri|sri|adv|capt|col|prof|late|m/s|jb|the|and|&)\b", re.I)
UNIT_IN_NAME = re.compile(r"\b([A-D])\s*[-/ ]?\s*(\d{2,4})\b")
SPLIT = re.compile(r"\s+and\s+|\s*&\s*|\s*\+\s*|\s*,\s*", re.I)


def norm_tokens(name: str) -> set:
    """Lowercase, drop honorifics + wing/unit tokens + single letters, return token set."""
    s = HONOR.sub(" ", str(name or "").lower())
    s = re.sub(r"\b[a-d]\s*[-/]?\s*\d{2,4}\b", " ", s)     # strip unit codes like A-1004
    s = re.sub(r"[^a-z ]", " ", s)
    toks = {t for t in s.split() if len(t) > 1}            # drop single letters / initials
    junk = {"imho", "imht", "okr", "wing", "owner", "tenant", "flat", "ora", "tower", "radiance"}
    return toks - junk


def sub_names(name: str) -> list[set]:
    """Split a multi-party string into per-person token sets (>=1 token each)."""
    out = []
    for part in SPLIT.split(str(name or "")):
        t = norm_tokens(part)
        if t:
            out.append(t)
    if not out:
        t = norm_tokens(name)
        if t:
            out = [t]
    return out


def unit_key(building: str, wing: str, number: str) -> str:
    # Wing may be a bare 'A' or a string like 'KALPATARU RADIANCE  D'. Take the
    # LAST standalone A-D token (the real wing), never a letter inside a word.
    toks = re.findall(r"\b([A-D])\b", (wing or "").upper())
    w = toks[-1] if toks else ""
    return f"{building}:{w}:{re.sub(r'[^0-9]', '', number or '')}"


def store_unit_hint(building: str, name: str, unit_raw: str) -> str:
    """Best (wing,number) we can read from the store row's name-prefix or unit_raw."""
    m = UNIT_IN_NAME.search(name or "") or UNIT_IN_NAME.search(unit_raw or "")
    if m:
        return f"{building}:{m.group(1).upper()}:{m.group(2)}"
    digits = re.sub(r"[^0-9]", "", unit_raw or "")
    return f"{building}::{digits}" if digits else ""


def load_store():
    """Return (by_token, cands, unit_phones). unit_phones maps a full unit key
    (building:wing:number) -> set of phones seen at that exact unit."""
    cands, by_token, unit_phones = [], defaultdict(list), defaultdict(set)
    unit_role_phones = defaultdict(lambda: defaultdict(set))  # unit -> role -> {phones}
    seen = set()
    for r in csv.DictReader(STORE.open()):
        ph = r["phone_e164"].strip()
        if not ph:
            continue
        # SRO document register is registrar-office metadata, not contacts.
        if "SRO_Document_Register" in r["source_file"] or re.search(r"\bS\.?R\.?\s*Mumbai|joint s", r["name"], re.I):
            continue
        b = r["building"]
        toks = norm_tokens(r["name"])
        if not toks:
            continue
        key = (ph, b, frozenset(toks))
        if key in seen:
            continue
        seen.add(key)
        c = {"phone": ph, "building": b, "tokens": toks,
             "unit": store_unit_hint(b, r["name"], r["unit_raw"]),
             "name": r["name"], "src": r["source_file"].split("/")[-1]}
        cands.append(c)
        for t in toks:
            by_token[t].append(c)
        if re.search(r":[A-D]:\d", c["unit"]):
            unit_phones[c["unit"]].add(ph)
            if r.get("role"):
                unit_role_phones[c["unit"]][r["role"]].add(ph)
    return by_token, cands, unit_phones, unit_role_phones


def _valid_phone(p):
    # reject obviously garbled numbers (14+ digits, +00 prefix). Pass D is
    # +91-only for stronger safety; Pass E leans on role+unit corroboration.
    d = re.sub(r"\D", "", p or "")
    return 10 <= len(d) <= 13 and not (p or "").startswith("+00")


def match_one(building, wing, number, full_name, by_token, unit_phones=None,
              role=None, unit_role_phones=None):
    """Return (phone, pass, confidence, evidence) or (None, reason, 0, evidence)."""
    tgt_unit = unit_key(building, wing, number)
    tgt_no = tgt_unit.rsplit(":", 1)[-1]
    best = None
    for sub in sub_names(full_name):
        if len(sub) < 1:
            continue
        # gather in-building candidates sharing >=1 token
        pool = {id(c): c for t in sub for c in by_token.get(t, []) if c["building"] == building}
        cand = []
        for c in pool.values():
            shared = len(sub & c["tokens"])
            if shared == 0:
                continue
            exact = sub == c["tokens"]
            # unit corroborates only if number matches AND wings don't conflict:
            # exact key match, or store row has no wing but same number.
            unit_ok = bool(tgt_no) and (
                c["unit"] == tgt_unit or c["unit"] == f"{building}::{tgt_no}")
            cand.append((c, shared, exact, unit_ok))
        if not cand:
            continue
        # Pass A: unit corroborates
        a = [c for c in cand if c[3]]
        if a:
            phones = {c[0]["phone"] for c in a}
            if len(phones) == 1:
                c = a[0][0]
                return c["phone"], "A", 0.97, f"unit+name:{c['name'][:40]}|{c['src']}"
        # Pass B: exact full-name, single phone
        b = [c for c in cand if c[2]]
        if b:
            phones = {c[0]["phone"] for c in b}
            if len(phones) == 1:
                cc = b[0][0]
                cbest = ("B", 0.9, cc)
                best = best or cbest
        # Pass C: >=2 shared tokens, single phone, no conflicting unit.
        strong = [c for c in cand if c[1] >= 2]
        phones = {c[0]["phone"] for c in strong}
        if strong and len(phones) == 1:
            cc = strong[0][0]
            # reject if this phone is tied to a specific unit that isn't the target's
            known = {c[0]["unit"] for c in strong if re.search(r":[A-D]:\d", c[0]["unit"])}
            conflict = bool(tgt_no) and known and tgt_unit not in known
            if not best and not conflict:
                best = ("C", 0.75, cc)
        elif len(phones) > 1:
            best = best or ("ambiguous", 0, None)
    if best and best[2]:
        p, conf, c = best[0], best[1], best[2]
        return c["phone"], p, conf, f"name:{c['name'][:40]}|{c['src']}"
    unit_specific = re.search(r":[A-D]:\d", tgt_unit)
    # Pass E: role-aware. Unit has several numbers, but exactly one is tagged with
    # the target's role (owner/tenant) -> pick that one.
    if role and unit_role_phones and unit_specific:
        rp = {p for p in unit_role_phones.get(tgt_unit, {}).get(role, set()) if _valid_phone(p)}
        if len(rp) == 1:
            return next(iter(rp)), "E", 0.75, f"unit+role({role}):{tgt_unit}"
    # Pass D: unit-authoritative. Unit has exactly ONE known phone. With no name
    # to corroborate, trust only clean +91 mobiles (garbled intl slips through
    # otherwise). Corroborated intl comes in via the name passes and Pass E.
    if unit_phones and unit_specific:
        ph = unit_phones.get(tgt_unit, set())
        if len(ph) == 1 and re.fullmatch(r"\+91[6-9]\d{9}", next(iter(ph))):
            return next(iter(ph)), "D", 0.7, f"unit-only:{tgt_unit}"
    return None, (best[0] if best else "no_match"), 0, ""


def load_targets():
    from _db import run_psql
    q = """
    select r.contact_id, b.name, bu.wing, bu.unit_number, c.full_name, r.relationship_type
    from contact_property_relationships r
    join buildings b on b.id=r.building_id
    join contacts c on c.id=r.contact_id
    join building_units bu on bu.id=r.building_unit_id
    where (b.name ilike '%imperial%' or b.name ilike '%kalpataru%')
      and coalesce(nullif(c.phone_primary,''), c.whatsapp_number) is null;"""
    rc, out = run_psql(q)
    if rc != 0:
        raise SystemExit("DB error: " + out)
    rows = []
    for line in out.splitlines():
        cid, bname, wing, unit, name, rel = (line.split("|") + [""] * 6)[:6]
        rows.append({"cid": cid, "building": "IH" if "imperial" in bname.lower() else "OKR",
                     "wing": wing, "unit": unit, "name": name, "role": rel.strip().lower()})
    return rows


def demo():
    assert norm_tokens("Mr. David Noronha") == {"david", "noronha"}
    assert norm_tokens("OKR D 123 Surindra Mahadev Rao") == {"surindra", "mahadev", "rao"}
    assert norm_tokens("(IMHO) Sudhir Bhagwant Wing B -3405") == {"sudhir", "bhagwant"}
    assert len(sub_names("Mrs. Mallika Gomes and Mr. Savio Gomes")) == 2
    assert unit_key("IH", "A", "1004").endswith(":A:1004")
    assert unit_key("OKR", "KALPATARU RADIANCE  D", "233") == "OKR:D:233", unit_key("OKR", "KALPATARU RADIANCE  D", "233")
    assert unit_key("OKR", "KALPATARU RADIANCE  C", "51") == "OKR:C:51"
    by = defaultdict(list)
    c = {"phone": "+919820212671", "building": "IH", "tokens": {"david", "noronha"},
         "unit": "IH:A:1004", "name": "David Noronha A 1004", "src": "x.csv"}
    for t in c["tokens"]:
        by[t].append(c)
    ph, p, conf, ev = match_one("IH", "A", "1004", "Mr. David Noronha", by)
    assert ph == "+919820212671" and p == "A", (ph, p)
    # ambiguous: two phones same name, no unit
    by2 = defaultdict(list)
    for ph_ in ("+911111111111", "+912222222222"):
        cc = {"phone": ph_, "building": "OKR", "tokens": {"asha", "devi"}, "unit": "", "name": "Asha Devi", "src": "y"}
        for t in cc["tokens"]:
            by2[t].append(cc)
    ph, p, conf, ev = match_one("OKR", "B", "281", "Asha Devi", by2)
    assert ph is None and p == "ambiguous", (ph, p)
    # Pass D: unit has exactly one phone, no name match -> attach by unit
    ph, p, conf, ev = match_one("IH", "A", "999", "Totally Unknown Person", defaultdict(list),
                                {"IH:A:999": {"+919000000000"}})
    assert ph == "+919000000000" and p == "D", (ph, p)
    # Pass D stays +91-only: an uncorroborated intl number does NOT attach
    ph, p, _, _ = match_one("IH", "A", "998", "X", defaultdict(list), {"IH:A:998": {"+971501234567"}})
    assert ph is None, (ph, p)
    # _valid_phone rejects the 14-digit garble, keeps clean +91 and intl
    assert not _valid_phone("+27059821156386") and _valid_phone("+919867743387") and _valid_phone("+971501234567")
    # Pass E: multi-phone unit, role picks the owner's number
    ph, p, _, _ = match_one("IH", "A", "997", "X", defaultdict(list),
                            {"IH:A:997": {"+919111111111", "+919222222222"}},
                            role="owner",
                            unit_role_phones={"IH:A:997": {"owner": {"+919111111111"},
                                                            "tenant": {"+919222222222"}}})
    assert ph == "+919111111111" and p == "E", (ph, p)
    print("ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        return demo()
    sys.path.insert(0, str(BASE / "scripts"))

    by_token, cands, unit_phones, unit_role_phones = load_store()
    targets = load_targets()
    matched, review = [], []
    stat = defaultdict(lambda: defaultdict(int))
    for t in targets:
        ph, p, conf, ev = match_one(t["building"], t["wing"], t["unit"], t["name"], by_token,
                                    unit_phones, t.get("role"), unit_role_phones)
        if ph and p in ("A", "B", "C", "D", "E"):
            matched.append({**t, "phone": ph, "pass": p, "conf": conf, "evidence": ev})
            stat[t["building"]][p] += 1
        else:
            review.append({**t, "reason": p, "evidence": ev})
            stat[t["building"]][p] += 1

    with REVIEW.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cid", "building", "wing", "unit", "name", "role", "reason", "evidence"])
        w.writeheader(); w.writerows(review)

    print(f"store phones: {len({c['phone'] for c in cands})}   targets: {len(targets)}")
    for b in ("IH", "OKR"):
        s = stat[b]
        att = s["A"] + s["B"] + s["C"] + s["D"] + s["E"]
        print(f"\n{b}: ATTACHABLE {att}  (A={s['A']} B={s['B']} C={s['C']} D={s['D']} E={s['E']})   "
              f"review: no_match={s['no_match']} ambiguous={s['ambiguous']}")
    print(f"\nreview -> {REVIEW}")
    print("sample matches:")
    for m in matched[:10]:
        print(f"  [{m['pass']}] {m['building']} {m['wing']}-{m['unit']:<5} {m['name'][:26]:<26} -> {m['phone']}  ({m['evidence'][:44]})")

    if not a.apply:
        print(f"\nDRY-RUN. {len(matched)} phones would attach. Re-run with --apply.")
        return
    apply_matches(matched)


def apply_matches(matched):
    from _db import run_psql, sql_literal as lit
    n = 0
    # batch the UPDATEs
    stmts = []
    for m in matched:
        meta = json.dumps({"phone_source": "building_contact_match", "match_pass": m["pass"],
                           "confidence": m["conf"], "evidence": m["evidence"], "batch": BATCH})
        stmts.append(
            f"update contacts set phone_primary={lit(m['phone'])}, "
            f"whatsapp_number=coalesce(nullif(whatsapp_number,''),{lit(m['phone'])}), "
            f"metadata=coalesce(metadata,'{{}}'::jsonb)||{lit(meta)}::jsonb, updated_at=now() "
            f"where id={lit(m['cid'])} and coalesce(nullif(phone_primary,''),whatsapp_number) is null;")
    # apply in chunks of 200
    for i in range(0, len(stmts), 200):
        chunk = "\n".join(stmts[i:i + 200])
        rc, out = run_psql("begin;\n" + chunk + "\ncommit;")
        if rc != 0:
            print("ERROR in chunk", i, out[:200]); return
        n += len(stmts[i:i + 200])
        print(f"  applied {n}/{len(stmts)}")
    print(f"DONE: attached {n} phones (batch {BATCH}). Reversible via metadata->>'batch'.")


if __name__ == "__main__":
    sys.exit(main())
