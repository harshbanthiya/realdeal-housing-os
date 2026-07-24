#!/usr/bin/env python3
"""Two-way sync between the sales phone and our DB (migration 073).

Her saved names already encode role + building + wing + unit in five different
dialects. This parses them, snapshots the phonebook, and proposes changes in
BOTH directions — never writing to her phone or to canonical tables.

  --selfcheck              parser regressions (run this first, it is the risk)
  --snapshot   [--apply]   load ~/Downloads/*.vcf into phonebook_snapshot
  --propose    [--apply]   generate review-gated proposals both directions
  --status                 what is pending

Canonical name format (operator's choice, role-first — docs/PHONEBOOK-PLAN.md):
    {ROLE}{BLDG} {WING}{UNIT} {Name}      e.g. "OIH A203 Abhijeet Anpat"
    BRK {Area} {Name}                     brokers have no unit
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db import jsonb_lit, run_psql, sql_literal as lit  # noqa: E402

PHONEBOOK_GLOB = str(Path.home() / "Downloads" / "*.vcf")

# Building code → canonical name. Codes are hers; keep them.
BLDG_CODE = {
    "IH": "Imperial Heights", "IMHO": "Imperial Heights", "IMH": "Imperial Heights",
    "KR": "Kalpataru Radiance", "OKR": "Kalpataru Radiance", "TKR": "Kalpataru Radiance",
    "ET": "Ekta Tripolis", "ETO": "Ekta Tripolis", "ETT": "Ekta Tripolis",
    "OE": "Oberoi Esquire", "OESQ": "Oberoi Esquire", "ESQ": "Oberoi Esquire",
    "DW": "DLF The Westpark", "WG": "Windsor Grande Residences",
}
CODE_FOR = {"Imperial Heights": "IH", "Kalpataru Radiance": "KR",
            "Ekta Tripolis": "ET", "Oberoi Esquire": "OE",
            "DLF The Westpark": "DW", "Windsor Grande Residences": "WG"}
ROLE_LETTER = {"owner": "O", "tenant": "T", "landlord": "L", "lead": "LD"}

# Building names written as words, not codes ("A 503 IH" vs "Client Imp ...").
BLDG_WORD = [
    (r"\bimperial\b|\bimp\b|\bimh\b", "Imperial Heights"),
    (r"\bkalpataru\b|\bradiance\b", "Kalpataru Radiance"),
    (r"\bekta\b|\btripolis\b", "Ekta Tripolis"),
    (r"\boberoi\b|\besquire\b", "Oberoi Esquire"),
    (r"\bwestpark\b|\bdlf\b", "DLF The Westpark"),
    (r"\bwindsor\b", "Windsor Grande Residences"),
]
# Role written as a word. These are NEVER part of the person's name.
ROLE_WORD = [
    (r"\bowner?s?\b|\bown\b", "owner"),
    (r"\btenants?\b|\bten\b|\brental?\b", "tenant"),
    (r"\bclients?\b|\bbuyers?\b|\benquiry\b", "lead"),
    (r"\bbrokers?\b|\bdalal\b", "broker"),
    (r"\blandlord\b|\bll\b", "landlord"),
]

# Junk names that carry no information.
JUNK = re.compile(r"^(extra\s*\d+|new\s*\d+|unknown|test|\.+|-+|\s*)$", re.I)

TEL_RE = re.compile(r"^TEL[^:]*:(.+)$", re.I)
FN_RE = re.compile(r"^FN[^:]*:(.+)$", re.I)


def norm_phone(raw: object) -> str | None:
    d = re.sub(r"\D", "", str(raw or "")).lstrip("0")
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    elif len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return "+91" + d if len(d) == 10 and d[0] in "6789" else None


def parse_name(raw: str) -> dict:
    """Her dialects → {role, building, wing, unit, person, confidence}.

    Dialects seen in her export:
      "(IMHO)  OD 2802 IH"        role+wing glued, building twice
      "(OEsq) Sagar Shah B 1103"  building in brackets, unit trailing
      "OKR C 72 Sagar Shah"       role+building glued, wing and unit split
      "OA 202 IH Abhijeet Anpat"  role+wing glued, building mid-string
      "TKR - 1"                   role+building only
      "ETO MANISH KUMAR / 2 BHK"  role+building glued, config noise
    """
    out = {"role": None, "building": None, "wing": None, "unit": None,
           "person": None, "confidence": "none"}
    if not raw or JUNK.match(raw.strip()):
        return out

    s = re.sub(r"\s+", " ", raw).strip()
    s = s.replace("(", " ").replace(")", " ")
    s = re.sub(r"/\s*\d+\s*BHK.*$", "", s, flags=re.I)      # drop "/ 2 BHK"
    s = re.sub(r"\s+-\s+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    tokens = s.split(" ")

    consumed = set()

    # Pass 1: a token that is role+building glued (OKR, TKR, ETO, IMHO, OEsq).
    for i, t in enumerate(tokens):
        up = t.upper().strip(".,")
        if up in BLDG_CODE:
            out["building"] = BLDG_CODE[up]
            consumed.add(i)
            if up.startswith("T"):
                out["role"] = "tenant"
            elif up.startswith("O") or up == "IMHO" or up.endswith("O"):
                out["role"] = "owner"
            continue
        # role letter + building code, e.g. "OKR" handled above; "OIH" here
        m = re.fullmatch(r"([OTL])([A-Z]{2,4})", up)
        if m and m.group(2) in BLDG_CODE:
            out["role"] = {"O": "owner", "T": "tenant", "L": "landlord"}[m.group(1)]
            out["building"] = BLDG_CODE[m.group(2)]
            consumed.add(i)

    # Pass 1b: building and role written as words rather than codes.
    low = s.lower()
    if out["building"] is None:
        for pat, name in BLDG_WORD:
            if re.search(pat, low):
                out["building"] = name
                for i, tok in enumerate(tokens):
                    if re.fullmatch(pat, tok.lower().strip(".,")):
                        consumed.add(i)
                break
    if out["role"] is None:
        for pat, role in ROLE_WORD:
            if re.search(pat, low):
                out["role"] = role
                break
    # Role words never belong to the person, whether or not they set the role.
    for i, tok in enumerate(tokens):
        for pat, _ in ROLE_WORD:
            if re.fullmatch(pat, tok.lower().strip(".,")):
                consumed.add(i)

    # Pass 2: role + wing glued to a single letter, e.g. "OD", "TA", "OA".
    for i, t in enumerate(tokens):
        if i in consumed:
            continue
        m = re.fullmatch(r"([OTL])([A-H])", t.upper())
        if m:
            out["role"] = out["role"] or {"O": "owner", "T": "tenant", "L": "landlord"}[m.group(1)]
            out["wing"] = m.group(2)
            consumed.add(i)
            break

    # Pass 3: wing+unit glued ("A203", "B1103") or a bare unit number.
    for i, t in enumerate(tokens):
        if i in consumed:
            continue
        m = re.fullmatch(r"([A-H])[\s-]?(\d{2,5})", t.upper())
        if m:
            out["wing"] = out["wing"] or m.group(1)
            out["unit"] = m.group(2)
            consumed.add(i)
            break
        if re.fullmatch(r"\d{2,5}", t) and out["unit"] is None:
            # A lone number is a unit only if a wing was already established, or
            # the previous token is a single letter wing.
            prev = tokens[i - 1].upper() if i else ""
            if out["wing"] or re.fullmatch(r"[A-H]", prev):
                if re.fullmatch(r"[A-H]", prev):
                    out["wing"] = prev
                    consumed.add(i - 1)
                out["unit"] = t
                consumed.add(i)
                break

    # Pass 4: a standalone wing letter.
    if out["wing"] is None:
        for i, t in enumerate(tokens):
            if i not in consumed and re.fullmatch(r"[A-H]", t.upper()):
                out["wing"] = t.upper()
                consumed.add(i)
                break

    # Whatever is left, that looks like words, is the person.
    person = " ".join(t for i, t in enumerate(tokens)
                      if i not in consumed and not re.fullmatch(r"[\d\W]+", t))
    person = re.sub(r"\s+", " ", person).strip(" .,-")
    if person and re.fullmatch(r"(?i)\s*(owner|tenant|client|broker|imperial|imp|mr|mrs|ms)\s*", person):
        person = ""
    out["person"] = person or None

    if out["building"] and out["unit"]:
        out["confidence"] = "high"
    elif out["building"] or out["unit"]:
        out["confidence"] = "medium"
    elif out["person"]:
        out["confidence"] = "low"
    return out


def canonical_name(role: str | None, building: str | None, wing: str | None,
                   unit: str | None, person: str | None) -> str | None:
    """Role-first canonical form. None when we lack enough to improve on hers."""
    if role == "broker":
        return f"BRK {person}".strip() if person else None
    if not building or not person:
        return None
    code = CODE_FOR.get(building)
    letter = ROLE_LETTER.get(role or "", "")
    if not code or not letter:
        return None
    unit_part = f"{wing or ''}{unit or ''}".strip()
    return " ".join(x for x in [f"{letter}{code}", unit_part, person] if x)


def read_cards() -> list[dict]:
    cards: list[dict] = []
    for path in sorted(glob.glob(PHONEBOOK_GLOB)):
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        blocks = [b for b in text.split("BEGIN:VCARD") if "END:VCARD" in b]
        for idx, block in enumerate(blocks):
            name, phone = "", None
            for line in block.splitlines():
                line = line.strip()
                m = FN_RE.match(line)
                if m:
                    name = m.group(1).strip()
                m = TEL_RE.match(line)
                if m and phone is None:
                    phone = norm_phone(m.group(1))
            if name or phone:
                cards.append({"file": Path(path).name, "index": idx,
                              "name": name, "phone": phone})
    return cards


def q(sql: str) -> list[list[str]]:
    code, out = run_psql(sql)
    if code != 0:
        sys.exit(f"error: {out[:500]}")
    return [ln.split("|") for ln in out.splitlines() if ln]


def snapshot(apply: bool) -> None:
    cards = read_cards()
    parsed = [(c, parse_name(c["name"])) for c in cards]
    hi = sum(1 for _, p in parsed if p["confidence"] == "high")
    med = sum(1 for _, p in parsed if p["confidence"] == "medium")
    print(f"cards: {len(cards)}  parsed high: {hi}  medium: {med}")
    if not apply:
        print("DRY RUN — pass --apply to write phonebook_snapshot.")
        for c, p in parsed[:8]:
            print(f"  {c['name'][:44]:<44} → {p['role']}/{p['building']}/"
                  f"{p['wing']}{p['unit'] or ''} · {p['person']}")
        return

    ids = {n: i for n, i in q("SELECT name, min(id::text) FROM buildings GROUP BY name")}
    today = date.today().isoformat()
    values = []
    for c, p in parsed:
        bid = ids.get(p["building"] or "")
        values.append("(" + ", ".join([
            lit(today), lit(c["file"]), str(c["index"]),
            lit(c["phone"]) if c["phone"] else "NULL",
            lit(c["name"][:200]),
            lit(p["role"]) if p["role"] else "NULL",
            (lit(bid) + "::uuid") if bid else "NULL",
            lit(p["wing"]) if p["wing"] else "NULL",
            lit(p["unit"]) if p["unit"] else "NULL",
            lit(p["person"][:120]) if p["person"] else "NULL",
            lit(p["confidence"]),
        ]) + ")")

    for i in range(0, len(values), 400):
        q(f"""INSERT INTO phonebook_snapshot
                (captured_on, source_file, card_index, phone, original_name,
                 parsed_role, parsed_building_id, parsed_wing, parsed_unit,
                 parsed_person, parse_confidence)
              VALUES {", ".join(values[i:i+400])}
              ON CONFLICT (captured_on, source_file, card_index) DO NOTHING""")
    print(f"status: ok\nsnapshot_rows: {len(values)}")


def propose(apply: bool) -> None:
    """Both directions. Everything lands as status='pending'."""
    if not apply:
        print("DRY RUN — counting only.")

    # --- Direction 1: DB → phone. We know a unit/role her card doesn't show.
    to_phone = q("""
        SELECT DISTINCT ON (s.phone)
               s.id::text, s.phone, s.original_name,
               b.name, u.wing, u.unit_number, r.relationship_type,
               c.id::text
          FROM phonebook_snapshot s
          JOIN contact_methods m
            ON regexp_replace(m.normalized_value,'\\D','','g')
             = regexp_replace(s.phone,'\\D','','g')
          JOIN contacts c ON c.id = m.contact_id
          JOIN contact_property_relationships r ON r.contact_id = c.id
          JOIN building_units u ON u.id = r.building_unit_id
          JOIN buildings b ON b.id = u.building_id
         WHERE s.phone IS NOT NULL
           AND s.captured_on = (SELECT max(captured_on) FROM phonebook_snapshot)
         ORDER BY s.phone, r.updated_at DESC""")

    rename_vals, n_rename = [], 0
    for sid, phone, orig, bldg, wing, unit, role, cid in to_phone:
        person = parse_name(orig)["person"] or orig
        newname = canonical_name(role, bldg, wing, unit, person)
        if not newname or newname == orig:
            continue
        n_rename += 1
        note = (f"— RDH —\\nWas saved as: {orig}\\n"
                f"Role: {role.title()} · {bldg} {wing or ''}-{unit}\\n"
                f"Updated: {date.today().isoformat()}")
        rename_vals.append("(" + ", ".join([
            lit(sid) + "::uuid", lit(phone), lit("to_phone"), lit("rename"),
            lit(orig[:200]), lit(newname[:200]), lit(note),
            lit(cid) + "::uuid", lit(role), lit("high"),
        ]) + ")")

    # --- Direction 2: phone → DB. Her name names a unit we have no phone for.
    to_db = q("""
        SELECT s.id::text, s.phone, s.original_name, u.id::text, b.name,
               s.parsed_wing, s.parsed_unit, coalesce(s.parsed_role,'owner')
          FROM phonebook_snapshot s
          JOIN buildings b ON b.id = s.parsed_building_id
          JOIN building_units u
            ON u.building_id = s.parsed_building_id
           AND upper(coalesce(u.wing,'')) = upper(coalesce(s.parsed_wing,''))
           AND regexp_replace(coalesce(u.unit_number,''),'\\D','','g')
             = regexp_replace(coalesce(s.parsed_unit,''),'\\D','','g')
         WHERE s.phone IS NOT NULL
           AND s.parse_confidence = 'high'
           AND s.captured_on = (SELECT max(captured_on) FROM phonebook_snapshot)
           -- only where we do NOT already have this phone on that unit
           AND NOT EXISTS (
                 SELECT 1 FROM contact_property_relationships r
                   JOIN contact_methods m2 ON m2.contact_id = r.contact_id
                  WHERE r.building_unit_id = u.id
                    AND regexp_replace(m2.normalized_value,'\\D','','g')
                      = regexp_replace(s.phone,'\\D','','g'))""")

    link_vals = []
    for sid, phone, orig, uid, bldg, wing, unit, role in to_db:
        link_vals.append("(" + ", ".join([
            lit(sid) + "::uuid", lit(phone), lit("to_db"), lit("link_unit"),
            lit(""), lit(f"{bldg} {wing or ''}-{unit} ({role})"),
            lit(f"From her phonebook: {orig}"),
            "NULL", lit(role), lit("medium"), lit(uid) + "::uuid",
        ]) + ")")

    print(f"to_phone renames proposed: {n_rename}")
    print(f"to_db unit links proposed: {len(link_vals)}")
    if not apply:
        for row in to_db[:6]:
            print(f"  phone {row[1]} → {row[4]} {row[5]}-{row[6]}  (from '{row[2][:40]}')")
        return

    for i in range(0, len(rename_vals), 300):
        q(f"""INSERT INTO phonebook_proposals
                (snapshot_id, phone, direction, change_type, current_value,
                 proposed_value, note_block, contact_id, role, confidence)
              VALUES {", ".join(rename_vals[i:i+300])}
              ON CONFLICT (phone, direction, change_type) DO NOTHING""")
    for i in range(0, len(link_vals), 300):
        q(f"""INSERT INTO phonebook_proposals
                (snapshot_id, phone, direction, change_type, current_value,
                 proposed_value, note_block, contact_id, role, confidence,
                 building_unit_id)
              VALUES {", ".join(link_vals[i:i+300])}
              ON CONFLICT (phone, direction, change_type) DO NOTHING""")
    print("status: ok")


def selfcheck() -> None:
    cases = [
        ("(IMHO)  OD 2802 IH", "owner", "Imperial Heights", "D", "2802"),
        ("(OEsq) Sagar Shah B 1103", "owner", "Oberoi Esquire", "B", "1103"),
        ("OKR C 72 Sagar Shah", "owner", "Kalpataru Radiance", "C", "72"),
        ("OA 202 IH Abhijeet Anpat", "owner", "Imperial Heights", "A", "202"),
        ("TA 3203 IH Aakansha Nimonkar", "tenant", "Imperial Heights", "A", "3203"),
        ("TKR - 1", "tenant", "Kalpataru Radiance", None, None),
    ]
    for raw, role, bldg, wing, unit in cases:
        got = parse_name(raw)
        assert got["role"] == role, (raw, got)
        assert got["building"] == bldg, (raw, got)
        assert got["wing"] == wing, (raw, got)
        assert got["unit"] == unit, (raw, got)

    # People survive parsing.
    assert parse_name("OA 202 IH Abhijeet Anpat")["person"] == "Abhijeet Anpat"
    assert parse_name("OKR C 72 Sagar Shah")["person"] == "Sagar Shah"

    # Junk stays junk — never invent a unit from "Extra 934".
    for junk in ("Extra 934", "OKR 85", ".", ""):
        p = parse_name(junk)
        assert p["person"] is None or p["confidence"] != "high", (junk, p)

    # Word-form buildings and roles (found in her real export).
    got = parse_name("Client Imp Smiritisingh A 2003")
    assert got["building"] == "Imperial Heights" and got["role"] == "lead", got
    assert got["wing"] == "A" and got["unit"] == "2003", got
    assert "Imp" not in (got["person"] or ""), got

    got = parse_name("A 503 IH Owner")
    assert got["role"] == "owner" and got["building"] == "Imperial Heights", got
    assert got["person"] is None, got          # "Owner" is a role, not a name

    got = parse_name("Owner Imperial Mr Modi A1002")
    assert got["role"] == "owner" and got["building"] == "Imperial Heights", got
    assert "Modi" in (got["person"] or ""), got

    # Canonical form, role-first.
    assert canonical_name("owner", "Imperial Heights", "A", "203", "Abhijeet Anpat") \
        == "OIH A203 Abhijeet Anpat"
    assert canonical_name("tenant", "Kalpataru Radiance", "C", "1104", "Sunil Gangwal") \
        == "TKR C1104 Sunil Gangwal"
    # Not enough to improve on hers → propose nothing.
    assert canonical_name("owner", None, None, None, "Someone") is None

    print("selfcheck: ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--propose", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:
        selfcheck()
    elif a.snapshot:
        snapshot(a.apply)
    elif a.propose:
        propose(a.apply)
    elif a.status:
        for row in q("SELECT direction, change_type, status, n::text "
                     "FROM vw_phonebook_sync_progress"):
            print("  " + "  ".join(row))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
