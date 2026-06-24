"""Parser QA report for Kalpataru Radiance IGR data.

Checks:
  1. Wing text coverage — are all values mapping to known wings?
  2. Party name sample per wing — 5 names each for human transliteration review
  3. Transliteration red flags — non-ASCII, suspiciously short, doubled consonants
  4. Unit coverage — how many units per wing have at least 1 registration

Usage:
  python scripts/qa_kalpataru_parser.py          # full report
  python scripts/qa_kalpataru_parser.py --wing A # single wing
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import run_psql  # noqa: E402

BUILDING_ID = 'f63d75ab-2ef9-48a9-afe2-cab3c4283283'

EXPECTED_WINGS = {
    'A': 'Ora',
    'B': 'Brilliance',
    'C': 'Allura',
    'D': 'Lumina',
    'E': 'shops (ground floor retail)',
}

# ── 1. Wing text coverage ──────────────────────────────────────────────────────
_WING_COVERAGE_SQL = f"""
SELECT COALESCE(wing_text,'(null)') as wing_text,
  SUBSTRING(wing_text FROM 'Wing ([A-Z])') as extracted,
  COUNT(*) as n
FROM unit_registration_records
WHERE building_id='{BUILDING_ID}'
GROUP BY wing_text ORDER BY n DESC;
"""

# ── 2. Party name sample per wing ─────────────────────────────────────────────
def _sample_sql(wing_letter: str, limit: int = 5) -> str:
    return f"""
SELECT p.party_name_raw, p.party_name_normalized, p.party_name_devanagari,
       p.party_role, urr.wing_text
FROM unit_registration_parties p
JOIN unit_registration_records urr ON urr.id = p.unit_registration_record_id
WHERE urr.building_id='{BUILDING_ID}'
  AND SUBSTRING(urr.wing_text FROM 'Wing ([A-Z])') = '{wing_letter}'
  AND p.party_name_raw IS NOT NULL
ORDER BY RANDOM()
LIMIT {limit};
"""

# ── 3. Transliteration flags ──────────────────────────────────────────────────
_FLAGS_SQL = f"""
SELECT issue, COUNT(*) as n FROM (
  SELECT
    CASE
      WHEN party_name_raw ~ '[^[:ascii:]]' AND party_name_normalized IS NULL THEN 'non_ascii_no_transliteration'
      WHEN party_name_normalized ~ '[^[:ascii:]]' THEN 'non_ascii_in_normalized'
      WHEN LENGTH(COALESCE(party_name_normalized, party_name_raw)) < 4 THEN 'suspiciously_short'
      WHEN party_name_normalized ~ '([A-Z])\\1{{2,}}' THEN 'triple_consonant_repeat'
      WHEN party_name_raw IS NULL THEN 'null_raw_name'
      ELSE 'ok'
    END AS issue
  FROM unit_registration_parties p
  JOIN unit_registration_records urr ON urr.id = p.unit_registration_record_id
  WHERE urr.building_id='{BUILDING_ID}'
) sub
GROUP BY issue ORDER BY n DESC;
"""

# ── 4. Unit coverage per wing ─────────────────────────────────────────────────
_COVERAGE_SQL = f"""
SELECT
  SUBSTRING(TRIM(bu.wing) FROM '[A-Z]$') as wing,
  COUNT(DISTINCT bu.id) as total_units,
  COUNT(DISTINCT urr.building_unit_id) as units_with_regs,
  ROUND(100.0 * COUNT(DISTINCT urr.building_unit_id) / NULLIF(COUNT(DISTINCT bu.id),0), 1) as pct
FROM building_units bu
LEFT JOIN unit_registration_records urr
  ON urr.building_unit_id = bu.id AND urr.building_id='{BUILDING_ID}'
WHERE bu.building_id='{BUILDING_ID}'
  AND bu.wing LIKE 'KALPATARU%'
GROUP BY 1 ORDER BY 1;
"""


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wing", choices=list(EXPECTED_WINGS.keys()),
                    help="Limit sample to one wing")
    args = ap.parse_args()

    # 1. Wing text coverage
    section("1. WING TEXT COVERAGE")
    _, out = run_psql(_WING_COVERAGE_SQL)
    known, unknown = [], []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 3:
            continue
        wing_text, extracted, n = parts[0], parts[1], parts[2]
        label = EXPECTED_WINGS.get(extracted, '???') if extracted else '(unmapped)'
        row = f"  {n:>6}  {wing_text:<30}  → wing={extracted or '?'} ({label})"
        if extracted in EXPECTED_WINGS or wing_text == '(null)':
            known.append(row)
        else:
            unknown.append(row)
    for r in known:
        print(r)
    if unknown:
        print("\n  ⚠ UNKNOWN WING VALUES:")
        for r in unknown:
            print(r)

    # 2. Party name samples
    wings = [args.wing] if args.wing else list(EXPECTED_WINGS.keys())
    for w in wings:
        section(f"2. PARTY NAME SAMPLE — Wing {w} ({EXPECTED_WINGS[w]})")
        _, out = run_psql(_sample_sql(w))
        if not out.strip():
            print("  (no records)")
            continue
        for line in out.splitlines():
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 3:
                continue
            raw, norm, deva, role = (parts + ['','','',''])[:4]
            print(f"  raw:  {raw}")
            print(f"  norm: {norm or '(none)'}")
            print(f"  deva: {deva or '(none)'}")
            print(f"  role: {role}")
            print()

    # 3. Transliteration flags
    section("3. TRANSLITERATION FLAGS")
    _, out = run_psql(_FLAGS_SQL)
    for line in out.splitlines():
        parts = [p.strip() for p in line.split('|')]
        if len(parts) == 2:
            issue, n = parts
            flag = "  ✓" if issue == 'ok' else "  ⚠"
            print(f"{flag}  {n:>6}  {issue}")

    # 4. Unit coverage
    section("4. UNIT COVERAGE PER WING")
    _, out = run_psql(_COVERAGE_SQL)
    for line in out.splitlines():
        parts = [p.strip() for p in line.split('|')]
        if len(parts) == 4:
            wing, total, with_regs, pct = parts
            name = EXPECTED_WINGS.get(wing, '?')
            print(f"  Wing {wing} ({name:<12})  {with_regs}/{total} units ({pct}%)")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
