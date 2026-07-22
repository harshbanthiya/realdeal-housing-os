#!/usr/bin/env python3
"""Guided per-doc IGR Index II capture — searches by SRO + Year + Document Number.

Reads tenancy records missing rent/deposit from the DB, then walks you through
each one: prints exactly what to enter in the free IGR document search form,
waits for you to fill it in and press Enter, then auto-clicks the IndexII button
and saves the snapshot.

Hard guards: headed browser only, no CAPTCHA bypass, no auto-fill, no DB writes.

Usage:
  python scripts/fetch_igr_docno_targeted.py                             # Kalpataru queue
  python scripts/fetch_igr_docno_targeted.py --building imperial_heights # IH queue
  python scripts/fetch_igr_docno_targeted.py --building imperial_heights --sro "Joint S.R. Mumbai 18"
  python scripts/fetch_igr_docno_targeted.py --apply --skip 5            # resume after 5

  # Apartments with zero DB records that the independent QA audit found a raw doc for
  # (run qa_independent_audit.py then --search-missing first):
  python scripts/fetch_igr_docno_targeted.py --source missing-units --building imperial_heights
  python scripts/fetch_igr_docno_targeted.py --source missing-units --building kalpataru --apply

  # Registrations attached to no apartment — mortgage deeds whose description names the land,
  # not a flat. Only the Index II's own "Apartment/Flat No" line can place them.
  python scripts/fetch_igr_docno_targeted.py --source unlinked --building kalpataru
  python scripts/fetch_igr_docno_targeted.py --source unlinked --building kalpataru --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from _db import run_psql

DEFAULT_URL = "https://freesearchigrservice.maharashtra.gov.in/"
INDEX2_BTN_SEL = "input[value='IndexII']"

# Exact selectors from playwright codegen recording (2026-06-28)
IGR_DISTRICT = "31"   # Mumbai Suburban
_SEL_CLOSE_POPUP  = "link:Close"                        # landing popup
_SEL_DOC_TAB      = "link:दस्त निहाय/Document Number"  # tab
_SEL_EREG_RADIO   = "radio:eRegistration"               # registration type
_SEL_DISTRICT     = "#ddldistrictfordoc"
_SEL_SRO          = "#ddlSROName"
_SEL_YEAR         = "#ddlYearForDoc"
_SEL_DOCNO        = "#txtDocumentNo"
_SEL_CAPTCHA      = "textbox:Enter captcha as shown"    # human fills this
_SEL_SEARCH       = "button:शोध / Search"

_BUILDING_FILTER = {
    "kalpataru": "b.name ILIKE '%kalpataru%radiance%'",
    "imperial_heights": "b.id = '0e72db71-8b93-4ecd-879c-17d8d8f2b206'",
    "ekta": "b.id = '2032514a-adef-4d2f-a12c-6ecf06853243'",
}
_SNAPSHOT_DIR = {
    "kalpataru": "igr_index2_snapshots",
    "imperial_heights": "igr_index2_snapshots_imperial_heights",
    "ekta": "igr_index2_snapshots_ekta",
}


def load_queue(building: str = "kalpataru", sro_filter: str | None = None) -> list[dict]:
    """Records with no Index II ever captured (stamp_duty NULL), tenancy records still
    missing rent / end-date / start-date, and records with a BLANK property_description_raw
    (with a known SRO).

    A blank description means the record's building was never actually confirmed --
    it was inserted via a doc-number/wing fallback during a bulk SRO-wide crawl, not a
    verified match. 2026-07-06: 6 such "Imperial Heights" records were docno-captured for
    real and turned out to belong to unrelated buildings on the same SRO (Roma Tower,
    Dattani Shelter, Kamla Gulmohar Heights, Dheeraj Residency) -- set aside to
    exports/ih_misfiled_setaside/. Blank-description rows are treated as unverified and
    requeued here regardless of whether stamp_duty/rent got backfilled by that same
    unreliable pass.

    Excludes SAMPLE% fixtures and 'Patra Chawl (MHADA rehab)' rows -- a different
    building's documents that had been mis-filed under Kalpataru's building_id (found and
    set aside 2026-07-06; see exports/patra_chawl_setaside/).
    """
    bldg_where = _BUILDING_FILTER.get(building, _BUILDING_FILTER["kalpataru"])
    sro_clause = f"AND r.sro_office ILIKE '%{sro_filter}%'" if sro_filter else ""
    _, out = run_psql(f"""
        SELECT
            r.doc_number,
            r.sro_office,
            COALESCE(EXTRACT(year FROM r.registration_date)::int,
                     r.registration_year)::int AS reg_year,
            COALESCE(bu.wing, r.wing_text, '') AS wing,
            COALESCE(bu.unit_number, r.unit_text, '') AS unit,
            r.registration_date::text,
            TRIM(
                CASE WHEN COALESCE(r.property_description_raw,'')='' THEN 'UNVERIFIED ' ELSE '' END ||
                CASE WHEN r.stamp_duty IS NULL THEN 'index2 ' ELSE '' END ||
                CASE WHEN r.transaction_category = 'tenancy' AND r.tenancy_monthly_rent IS NULL THEN 'rent ' ELSE '' END ||
                CASE WHEN r.transaction_category = 'tenancy' AND r.tenancy_end_date   IS NULL THEN 'end-date ' ELSE '' END ||
                CASE WHEN r.transaction_category = 'tenancy' AND r.tenancy_start_date IS NULL THEN 'start-date' ELSE '' END
            ) AS gap,
            r.tenancy_monthly_rent::text,
            r.tenancy_start_date::text,
            r.tenancy_end_date::text
        FROM unit_registration_records r
        JOIN buildings b ON b.id = r.building_id
        LEFT JOIN building_units bu ON bu.id = r.building_unit_id
        WHERE {bldg_where}
          AND (
                r.stamp_duty IS NULL
                OR COALESCE(r.property_description_raw,'') = ''
                OR (r.transaction_category = 'tenancy'
                    AND (r.tenancy_monthly_rent IS NULL OR r.tenancy_end_date IS NULL OR r.tenancy_start_date IS NULL))
              )
          AND r.doc_number NOT LIKE 'SAMPLE%%'
          AND COALESCE(r.wing_text, '') NOT ILIKE 'Patra Chawl%%'
          AND r.sro_office IS NOT NULL AND r.sro_office != ''
          {sro_clause}
        ORDER BY r.sro_office, r.registration_date, r.doc_number::int
    """)
    rows = []
    for line in out.strip().splitlines():
        parts = line.split('|')
        if len(parts) < 10:
            continue
        doc, sro, year, wing, unit, date, gap, rent, start, end = [p.strip() for p in parts[:10]]
        rows.append({
            'doc': doc,
            'sro': sro,
            'year': year or (date[:4] if date else '?'),
            'wing': wing,
            'unit': unit.rstrip(',').strip(),
            'date': date[:10] if date else '',
            'gap': gap,
            'rent': rent,
            'start': start,
            'end': end,
        })
    return rows


_MISSING_UNITS_DIR = PROJECT_ROOT / "exports" / "qa_independent_audit"


def load_unlinked_queue(building: str = "kalpataru", sro_filter: str | None = None) -> list[dict]:
    """Registrations still attached to NO apartment, ordered oldest-first.

    These are mostly mortgage deeds whose property description names the land, not a flat,
    so no text parsing can place them: only the Index II's own "Apartment/Flat No" line can.
    Each already carries doc number + year + SRO, which is exactly what the document search
    needs. Records with an Index II capture already on disk are excluded — re-fetching them
    would tell us nothing new.
    """
    bldg_where = _BUILDING_FILTER.get(building, _BUILDING_FILTER["kalpataru"])
    sro_clause = f"AND r.sro_office ILIKE '%{sro_filter}%'" if sro_filter else ""
    _, out = run_psql(f"""
        SELECT r.doc_number, r.sro_office,
               COALESCE(EXTRACT(year FROM r.registration_date)::int, r.registration_year)::int,
               COALESCE(r.wing_text, ''), COALESCE(r.unit_text, ''),
               r.registration_date::text, COALESCE(r.transaction_category, '-')
        FROM unit_registration_records r
        JOIN buildings b ON b.id = r.building_id
        WHERE {bldg_where}
          AND r.building_unit_id IS NULL
          AND COALESCE(r.doc_number,'') <> ''
          AND COALESCE(r.sro_office,'') <> ''
          AND r.doc_number NOT LIKE 'SAMPLE%%'
          {sro_clause}
        ORDER BY r.registration_date;""")

    snap_dir = PROJECT_ROOT / "exports" / _SNAPSHOT_DIR.get(building, 'igr_index2_snapshots')
    captured = {m.group(1) + "/" + m.group(2)
                for p in snap_dir.rglob("capture_*_doc*_r*.txt")
                if (m := re.search(r"_doc(\d+)_(\d{4})_r\d+\.txt$", p.name))}

    rows = []
    for c in (ln.split("|") for ln in out.strip().splitlines() if ln.strip()):
        if len(c) < 7:
            continue
        doc, sro, year = c[0].strip(), c[1].strip(), c[2].strip()
        if f"{doc}/{year}" in captured:
            continue
        rows.append({'doc': doc, 'sro': sro, 'year': year,
                     'wing': c[3].strip(), 'unit': c[4].strip(), 'date': c[5].strip(),
                     'gap': f"unlinked ({c[6].strip()})", 'rent': '', 'start': '', 'end': ''})
    return rows


def load_missing_units_queue(building: str = "kalpataru") -> list[dict]:
    """Apartments with zero DB records where the independent QA audit
    (scripts/qa_independent_audit.py --search-missing) found a raw Index II .txt
    capture on disk naming this building, but the doc was never (or couldn't be)
    inserted -- e.g. its only source is an xls results-grid row (no Index II
    financial detail) so it still needs a real per-doc capture to verify and enrich.

    Requires exports/qa_independent_audit/missing_units_found_{building}.json to exist
    (run `python scripts/qa_independent_audit.py` then `--search-missing` first).
    """
    key = {"kalpataru": "kalpataru_radiance", "imperial_heights": "imperial_heights"}.get(building, building)
    path = _MISSING_UNITS_DIR / f"missing_units_found_{key}.json"
    if not path.exists():
        print(f"  [missing-units] {path} not found -- run qa_independent_audit.py "
              f"then --search-missing first.")
        return []
    found = json.loads(path.read_text(encoding="utf-8"))

    seen: set[tuple] = set()
    rows = []
    for u in found:
        for c in u.get("raw_candidates", []):
            dkey = (c["doc_no"], c["year"], c.get("sro_norm"))
            if dkey in seen:
                continue
            seen.add(dkey)
            rows.append({
                'doc': c['doc_no'],
                'sro': c['sro_raw'] or '',
                'year': c['year'],
                'wing': u['wing'] or '',
                'unit': (u['unit_number'] or '').rstrip(',').strip(),
                'date': '',
                'gap': f"never captured ({c['raw_kind']})",
                'rent': '', 'start': '', 'end': '',
            })
    rows.sort(key=lambda r: (r['sro'], r['year'], r['doc']))
    return rows


def safe_label(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]', '_', s)[:40]




_DEVA_RE   = re.compile(r'[ऀ-ॿ]')
_DEVA_CITY = {'मुंबई': 'Mumbai', 'बोरिवली': 'Borivali', 'ठाणे': 'Thane', 'पुणे': 'Pune'}

def _normalise_sro(s: str) -> str:
    for deva, en in _DEVA_CITY.items():
        s = s.replace(deva, en)
    return s


def _load_sro_options(page) -> list[dict]:
    """Return all non-blank SRO dropdown options as [{v, t}]."""
    try:
        return page.evaluate(f"""
            () => Array.from(document.querySelector('{_SEL_SRO}')?.options || [])
                .map(o => ({{v: o.value, t: o.text.trim()}}))
                .filter(o => o.v && o.v !== '0')
        """)
    except Exception:
        return []


def _pick_sro(page, sro_text: str) -> str | None:
    """Select the SRO dropdown option that best matches sro_text.

    Strategy:
    1. Extract trailing number ("Joint S.R. Mumbai 18" → "18").
    2. Also extract locality word ("Mumbai", "Borivali", etc.).
    3. Try to match both in option text (locality + number).
    4. Fall back to number-only match if needed.
    5. If still no match, print numbered list and let operator type index.
    Returns the matched option text, or None on give-up.
    """
    sro_norm = _normalise_sro(sro_text.strip())
    m_num = re.search(r'(\d+)\s*$', sro_norm)
    if not m_num:
        return None
    num = m_num.group(1)
    # Extract locality word — first capitalised word that isn't Joint/Sub/S/R
    m_loc = re.search(r'\b(Mumbai|Borivali|Thane|Pune|Nashik|Aurangabad)\b', sro_norm, re.I)
    locality = m_loc.group(1) if m_loc else ""

    options = _load_sro_options(page)
    if not options:
        print(f"  [sro] dropdown empty or not loaded yet")
        return None

    num_re = re.compile(r'(?<!\d)' + re.escape(num) + r'(?!\d)')

    # Pass 1: city name immediately followed by the number (e.g. "Mumbai 10" not "Borivali 10")
    if locality:
        tight_re = re.compile(re.escape(locality) + r'\s+' + re.escape(num) + r'(?!\d)', re.I)
        for opt in options:
            if tight_re.search(opt['t']):
                page.locator(_SEL_SRO).select_option(value=opt['v'])
                return opt['t']

    # Pass 2: number only (skip ambiguous single-digit matches like "8" matching "18")
    candidates = [o for o in options if num_re.search(o['t'])]
    if len(candidates) == 1:
        page.locator(_SEL_SRO).select_option(value=candidates[0]['v'])
        return candidates[0]['t']

    # Pass 3: print numbered list, let operator type index
    print(f"\n  [sro] could not auto-match {sro_text!r}. Available options:")
    for i, opt in enumerate(options):
        print(f"    {i+1:3}.  {opt['t']}")
    while True:
        try:
            raw = input(f"  → Type option number (1-{len(options)}) or s to skip: ").strip()
        except EOFError:
            return None
        if raw.lower() == 's':
            return None
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                page.locator(_SEL_SRO).select_option(value=options[idx]['v'])
                return options[idx]['t']
        except ValueError:
            pass
        print("  Invalid — enter a number from the list.")


def navigate_to_doc_tab(page, reg_type: str = "eRegistration") -> None:
    """Setup: dismiss popup, activate Document Number tab, select registration type + district."""
    try:
        page.get_by_role("link", name="Close").click(timeout=4000)
        page.wait_for_timeout(300)
    except Exception:
        pass
    try:
        page.get_by_role("link", name="दस्त निहाय/Document Number").click(timeout=6000)
        page.wait_for_timeout(500)
    except Exception:
        print("  [nav] doc-number tab not found — may already be active")
    try:
        page.get_by_role("radio", name=reg_type).check(timeout=4000)
        page.wait_for_timeout(300)
    except Exception:
        print(f"  [nav] radio {reg_type!r} not found")
    try:
        page.locator(_SEL_DISTRICT).select_option(IGR_DISTRICT)
        page.wait_for_timeout(800)
    except Exception as e:
        print(f"  [nav] district select failed: {e}")


def fill_form(page, r: dict) -> bool:
    """Fill SRO + Year + Doc No. Returns True if all three filled."""
    ok = True

    # SRO
    sro_matched = _pick_sro(page, r['sro'])
    if sro_matched:
        print(f"  [sro]   {sro_matched!r}")
    else:
        print(f"  [sro]   no match for {r['sro']!r} — select manually, then press Enter")
        try:
            input("  → (select SRO in browser, press Enter): ")
        except EOFError:
            pass
        ok = False

    # Year
    try:
        page.locator(_SEL_YEAR).select_option(str(r['year']))
        print(f"  [year]  {r['year']}")
    except Exception as e:
        print(f"  [year]  failed ({e}) — set manually")
        ok = False

    # Doc No
    try:
        page.locator(_SEL_DOCNO).fill(str(r['doc']))
        print(f"  [doc]   {r['doc']}")
    except Exception as e:
        print(f"  [doc]   failed ({e}) — enter manually")
        ok = False

    return ok


def save_page(context, page, out_dir: Path, prefix: str, written: list, captures: list) -> None:
    """Click all IndexII buttons and save each popup."""
    # Wait up to 5s for at least one IndexII button to appear
    try:
        page.wait_for_selector(INDEX2_BTN_SEL, timeout=5000)
    except Exception:
        pass

    btn_count = page.locator(INDEX2_BTN_SEL).count()
    print(f"  {btn_count} IndexII button(s) found")

    for btn_idx in range(btn_count):
        live = next((pg for pg in context.pages if not pg.is_closed()), None)
        if live is None:
            break
        idx2_prefix = f"{prefix}_r{btn_idx}"
        try:
            btn = live.locator(INDEX2_BTN_SEL).nth(btn_idx)
            with context.expect_page(timeout=15000) as popup_info:
                btn.click()
            popup = popup_info.value
            try:
                popup.wait_for_load_state('networkidle', timeout=15000)
            except Exception:
                pass
            for ext, fn in [
                ('.html', lambda pg=popup: pg.content()),
                ('.txt',  lambda pg=popup: pg.inner_text('body')),
            ]:
                try:
                    (out_dir / f"{idx2_prefix}{ext}").write_text(fn(), encoding='utf-8')
                    written.append(f"{idx2_prefix}{ext}")
                except Exception:
                    pass
            captures.append({'prefix': idx2_prefix})
            print(f"  saved IndexII → {idx2_prefix}")
            popup.close()
        except Exception as e:
            print(f"  IndexII {btn_idx} failed: {e}")


def print_queue(queue: list[dict], skip: int) -> None:
    print(f"\n{'':>3} {'#':<4} {'Year':<6} {'SRO':<24} {'Doc':<8} {'Wing':<8} {'Unit':<8} {'Rent':<12} {'Start':<12} {'End':<12} Missing")
    print('─' * 120)
    for i, r in enumerate(queue):
        done = '✓' if i < skip else ' '
        wing_short = r['wing'].replace('KALPATARU RADIANCE  ', '').strip() or '?'
        print(
            f"  {done} {i+1:<4} {r['year']:<6} {r['sro'][:22]:<24} {r['doc']:<8} "
            f"{wing_short:<8} {r['unit'][:6]:<8} "
            f"{(r['rent'] or '—')[:10]:<12} {(r['start'] or '—')[:10]:<12} {(r['end'] or '—')[:10]:<12} "
            f"{r['gap']}"
        )
    remaining = len(queue) - skip
    print(f"\n  Total: {len(queue)}  |  To capture: {remaining}  |  Skipped: {skip}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Guided per-doc IGR Index II capture.")
    ap.add_argument('--url', default=DEFAULT_URL)
    ap.add_argument('--apply', action='store_true', help='open browser and capture')
    ap.add_argument('--skip', type=int, default=0, metavar='N',
                    help='skip first N docs in the queue (use to resume a session)')
    ap.add_argument('--output-label', default='docno_targeted')
    ap.add_argument('--building', default='kalpataru',
                    choices=['kalpataru', 'imperial_heights', 'ekta'],
                    help='which building to queue (default: kalpataru)')
    ap.add_argument('--sro', default=None, metavar='NAME',
                    help='filter queue to a specific SRO (partial match, e.g. "Mumbai 18")')
    ap.add_argument('--deva-only', action='store_true',
                    help='only process records whose SRO is in Devanagari script')
    ap.add_argument('--source', default='gaps', choices=['gaps', 'missing-units', 'unlinked'],
                    help="'gaps' (default): tenancy records missing rent/dates from the DB. "
                         "'missing-units': apartments with zero DB records that the independent "
                         "QA audit found a raw doc for on disk (needs qa_independent_audit.py "
                         "--search-missing to have been run first)")
    args = ap.parse_args()

    snap_subdir = _SNAPSHOT_DIR.get(args.building, 'igr_index2_snapshots')
    snapshot_root = PROJECT_ROOT / "exports" / snap_subdir

    if args.source == 'missing-units':
        queue = load_missing_units_queue(args.building)
        if args.sro:
            queue = [r for r in queue if args.sro.lower() in r['sro'].lower()]
    elif args.source == 'unlinked':
        queue = load_unlinked_queue(args.building, args.sro)
    else:
        queue = load_queue(args.building, args.sro)
    if args.deva_only:
        queue = [r for r in queue if _DEVA_RE.search(r['sro'])]
    if not queue:
        msg = {"missing-units": "No apartments with a raw doc pending capture — nothing to do.",
               "unlinked": "No unlinked registrations left to capture — nothing to do.",
               }.get(args.source, "No tenancy records missing rent with a known SRO — nothing to do.")
        print(msg)
        return 0

    print_queue(queue, args.skip)

    if not args.apply:
        print("\nDry run — no browser opened. Re-run with --apply to start capturing.")
        return 0

    remaining = queue[args.skip:]
    if not remaining:
        print("\nAll docs already skipped. Lower --skip or run ingest first.")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("Playwright not installed.  Run: python3 -m playwright install chromium")
        return 2

    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    folder_ts  = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = snapshot_root / f"{folder_ts}_{safe_label(args.output_label)}_bulk"
    out_dir.mkdir(parents=True, exist_ok=True)

    captures: list[dict] = []
    errors:   list[str]  = []
    written:  list[str]  = []

    print(f"\nSnapshot folder: {out_dir}")
    print(f"Script fills SRO + Year + Doc No. For each doc:")
    print(f"  1. Solve CAPTCHA + click Search in the browser")
    print(f"  2. Press Enter here — script grabs IndexII then reloads the form")
    print(f"  Type 's' to skip, 'done' to quit.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page    = context.new_page()
        page.goto(args.url, timeout=60000, wait_until='domcontentloaded')
        page.wait_for_timeout(1500)

        for idx, r in enumerate(remaining):
            abs_num  = args.skip + idx + 1
            total    = len(queue)
            is_deva  = bool(_DEVA_RE.search(r['sro']))
            reg_type = "Regular" if is_deva else "eRegistration"

            navigate_to_doc_tab(page, reg_type)

            print(f"┌── Doc {abs_num}/{total} ─────────────────────────────────────────")
            print(f"│  SRO  {r['sro']}  ·  Year {r['year']}  ·  Doc {r['doc']}  [{reg_type}]")
            print(f"│  Flat {r['wing'] or '?'} {r['unit']}  (registered {r['date']})")
            print(f"└────────────────────────────────────────────────────────────────")

            fill_form(page, r)

            print(f"  Solve CAPTCHA + click Search in browser, then press Enter.")
            print(f"  (s=skip  done=quit)")
            try:
                cmd = input("  → ").strip().lower()
            except EOFError:
                break
            if cmd in ('done', 'q', 'quit', 'exit'):
                print("Stopping.")
                break
            if cmd == 's':
                print("  Skipped.\n")
                continue

            prefix = f"capture_{abs_num:03d}_doc{r['doc']}_{r['year']}"
            save_page(context, page, out_dir, prefix, written, captures)
            print()

            # Reload fresh form for next doc (navigate_to_doc_tab runs at top of next iteration)
            page = next((pg for pg in context.pages if not pg.is_closed()), None)
            if page is None:
                break
            page.goto(args.url, timeout=60000, wait_until='domcontentloaded')
            page.wait_for_timeout(1500)

        context.close()
        browser.close()

    metadata = {
        'capture_type': 'index2_targeted_docno',
        'url': args.url,
        'started_at': started_at,
        'method': 'playwright-autofill-per-doc',
        'output_label': args.output_label,
        'total_docs_in_queue': len(queue),
        'docs_attempted': len(remaining),
        'skip': args.skip,
        'capture_count': len(captures),
        'error_count': len(errors),
        'captures': captures,
        'errors': errors,
        'files_written': written,
        'captcha_solved_by_human': True,
        'trusted_for_db': False,
        'human_review_required': True,
        'db_writes': False,
        'note': (
            'Targeted doc-number captures. Files named capture_NNN_*_r0.txt '
            'so ingest_igr_bulk_snapshots.py picks them up automatically.'
        ),
    }
    (out_dir / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')

    print(f"\n── Session complete ──")
    print(f"  Snapshot folder : {out_dir}")
    print(f"  Captures saved  : {len(captures)}")
    print(f"  Errors          : {len(errors)}")
    for e in errors:
        print(f"    {e}")
    if captures:
        print(f"\nNext step:")
        print(f"  python scripts/ingest_igr_bulk_snapshots.py --apply --real-ok")
    print("  trusted_for_db=false  human_review_required=true  db_writes=false")
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
