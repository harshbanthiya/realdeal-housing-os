"""Fix two parser artifacts in unit_registration_parties for Kalpataru Radiance.

  1. Leading '--' prefix: strip from party_name_raw + party_name_normalized
     (IGR portal injects '--' before certain company names in HTML cells)

  2. Failed transliteration: 29 records where party_name_normalized is still
     Devanagari — re-run transliteration and update

Usage:
  python scripts/repair_party_name_artifacts.py          # dry run
  python scripts/repair_party_name_artifacts.py --apply  # write
"""
from __future__ import annotations
import argparse, re, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import run_psql  # noqa: E402

BUILDING_ID = 'f63d75ab-2ef9-48a9-afe2-cab3c4283283'

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate as _translit

DEVANAGARI = re.compile(r"[ऀ-ॿ]")

def ascii_fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def translit_name(raw: str) -> str:
    if not raw:
        return ""
    if DEVANAGARI.search(raw):
        try:
            out = _translit(raw, sanscript.DEVANAGARI, sanscript.IAST)
        except Exception:
            out = raw
    else:
        out = raw
    return re.sub(r"\s+", " ", ascii_fold(out)).strip().lower()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    # ── 1. Fetch all party IDs needing repair ─────────────────────────────────
    _, rows = run_psql(f"""
SELECT p.id, p.party_name_raw, p.party_name_normalized
FROM unit_registration_parties p
JOIN unit_registration_records urr ON urr.id = p.unit_registration_record_id
WHERE urr.building_id = '{BUILDING_ID}'
  AND (
    p.party_name_raw LIKE '--%'
    OR p.party_name_normalized ~ '[^[:ascii:]]'
  )
ORDER BY p.id;
""")

    fixes: list[tuple[str, str, str]] = []  # (id, new_raw, new_norm)
    for line in rows.splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        pid, raw, norm = parts[0].strip(), parts[1].strip(), parts[2].strip()

        # Strip leading '--'
        new_raw = re.sub(r"^--\s*", "", raw)
        new_norm = re.sub(r"^--\s*", "", norm)

        # Re-transliterate if normalized is still non-ASCII
        if DEVANAGARI.search(new_norm):
            new_norm = translit_name(new_raw)

        fixes.append((pid, new_raw, new_norm))

    dash_count = sum(1 for _, r, _ in fixes if r != re.sub(r"^--\s*", "", r) or True
                     if re.match(r"^--", r))
    retranslit_count = sum(1 for pid, raw, norm in fixes
                           if not DEVANAGARI.search(norm) and DEVANAGARI.search(
                               [p.split("|") for p in rows.splitlines()
                                if p.split("|")[0].strip() == pid][0][1] if any(
                                    p.split("|")[0].strip() == pid for p in rows.splitlines()
                                ) else ""))

    print(f"Records to fix: {len(fixes)}")
    # Simpler counts:
    orig = {p.split('|')[0].strip(): (p.split('|')[1].strip(), p.split('|')[2].strip())
            for p in rows.splitlines() if len(p.split('|')) >= 3}
    dash_fix = sum(1 for pid, nr, nn in fixes if orig.get(pid, ('',''))[0].startswith('--'))
    retrans_fix = sum(1 for pid, nr, nn in fixes if DEVANAGARI.search(orig.get(pid, ('',''))[1]))
    print(f"  leading '--' stripped:         {dash_fix}")
    print(f"  re-transliterated:             {retrans_fix}")

    if not fixes:
        print("Nothing to fix.")
        return 0

    # Preview first 5
    print("\nSample fixes:")
    for pid, new_raw, new_norm in fixes[:5]:
        old_raw, old_norm = orig.get(pid, ('',''))
        print(f"  raw:  {old_raw!r} → {new_raw!r}")
        print(f"  norm: {old_norm!r} → {new_norm!r}")
        print()

    if not args.apply:
        print(f"Dry run — {len(fixes)} record(s) would be updated. Re-run with --apply.")
        return 0

    # ── 2. Apply in one transaction ───────────────────────────────────────────
    cases_raw  = "\n".join(f"    WHEN id='{pid}' THEN {esc(nr)}" for pid, nr, _ in fixes)
    cases_norm = "\n".join(f"    WHEN id='{pid}' THEN {esc(nn)}" for pid, _, nn in fixes)
    ids = ",".join(f"'{pid}'" for pid, _, _ in fixes)

    sql = f"""
UPDATE unit_registration_parties
SET
  party_name_raw        = CASE {cases_raw} END,
  party_name_normalized = CASE {cases_norm} END,
  updated_at            = now()
WHERE id IN ({ids});
"""
    code, out = run_psql(sql)
    if code != 0:
        print(f"Error: {out}")
        return 1

    print(f"Applied — {len(fixes)} party name records repaired.")
    return 0


def esc(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


if __name__ == "__main__":
    sys.exit(main())
