#!/usr/bin/env python3
"""Guided per-doc IGR Index II capture — searches by SRO + Year + Document Number.

Reads tenancy records missing rent/deposit from the DB, then walks you through
each one: prints exactly what to enter in the free IGR document search form,
waits for you to fill it in and press Enter, then auto-clicks the IndexII button
and saves the snapshot.

Hard guards: headed browser only, no CAPTCHA bypass, no auto-fill, no DB writes.
Snapshots saved to: exports/igr_index2_snapshots/<ts>_docno_targeted_bulk/
Files named capture_NNN_*_r0.txt so the existing ingest script picks them up.

Usage:
  python scripts/fetch_igr_docno_targeted.py              # show queue, dry-run
  python scripts/fetch_igr_docno_targeted.py --apply      # open browser + capture
  python scripts/fetch_igr_docno_targeted.py --apply --skip 5   # resume after 5 docs
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PROJECT_ROOT / "exports" / "igr_index2_snapshots"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from _db import run_psql

DEFAULT_URL = "https://freesearchigrservice.maharashtra.gov.in/"
INDEX2_BTN_SEL = "input[value='IndexII']"


def load_queue() -> list[dict]:
    """Tenancy records missing any of rent / end-date / start-date, with a known SRO."""
    _, out = run_psql("""
        SELECT
            r.doc_number,
            r.sro_office,
            EXTRACT(year FROM r.registration_date)::int AS reg_year,
            COALESCE(bu.wing, r.wing_text, '') AS wing,
            COALESCE(bu.unit_number, r.unit_text, '') AS unit,
            r.registration_date::text,
            TRIM(
                CASE WHEN r.tenancy_monthly_rent IS NULL THEN 'rent ' ELSE '' END ||
                CASE WHEN r.tenancy_end_date   IS NULL THEN 'end-date ' ELSE '' END ||
                CASE WHEN r.tenancy_start_date IS NULL THEN 'start-date' ELSE '' END
            ) AS gap,
            r.tenancy_monthly_rent::text,
            r.tenancy_start_date::text,
            r.tenancy_end_date::text
        FROM unit_registration_records r
        JOIN buildings b ON b.id = r.building_id
        LEFT JOIN building_units bu ON bu.id = r.building_unit_id
        WHERE b.name ILIKE '%kalpataru%radiance%'
          AND COALESCE(r.transaction_category, registration_category(r.document_type)) = 'tenancy'
          AND (r.tenancy_monthly_rent IS NULL OR r.tenancy_end_date IS NULL OR r.tenancy_start_date IS NULL)
          AND r.doc_number NOT LIKE 'SAMPLE%%'
          AND r.sro_office IS NOT NULL AND r.sro_office != ''
          AND COALESCE(bu.wing, r.wing_text, '') NOT ILIKE '%%Patra%%'
          AND COALESCE(bu.wing, r.wing_text, '') NOT ILIKE '%%MHADA%%'
        ORDER BY r.registration_date, r.doc_number
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


def safe_label(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]', '_', s)[:40]


def detect_captcha(page) -> bool:
    try:
        return bool(page.locator(
            "img[src*='captcha'], input[id*='captcha'], #captcha, .captcha, "
            "[id*='CaptchaImage'], [id*='captchaImage']"
        ).count())
    except Exception:
        return False


def pause_if_captcha(page) -> None:
    if detect_captcha(page):
        print("\n  *** CAPTCHA detected — solve it in the browser, then press Enter ***")
        try:
            input("  (press Enter after solving CAPTCHA): ")
        except EOFError:
            pass


def save_page(context, page, out_dir: Path, prefix: str, written: list, captures: list) -> None:
    """Save results page + click all IndexII buttons, saving each popup."""
    captcha_here = detect_captcha(page)

    # Save results page
    for ext, fn in [
        ('.html', lambda: page.content()),
        ('.txt',  lambda: page.inner_text('body')),
    ]:
        try:
            data = fn()
            (out_dir / f"{prefix}_results{ext}").write_text(data, encoding='utf-8')
            written.append(f"{prefix}_results{ext}")
        except Exception:
            pass

    try:
        page.wait_for_selector(INDEX2_BTN_SEL, timeout=10000)
    except Exception:
        pass

    btn_count = page.locator(INDEX2_BTN_SEL).count()
    print(f"  {btn_count} IndexII button(s) found")

    for btn_idx in range(btn_count):
        # Re-acquire live page in case a popup shifted focus
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
                    data = fn()
                    (out_dir / f"{idx2_prefix}{ext}").write_text(data, encoding='utf-8')
                    written.append(f"{idx2_prefix}{ext}")
                except Exception:
                    pass
            captures.append({'prefix': idx2_prefix, 'captcha': captcha_here, 'type': 'popup'})
            print(f"  saved IndexII → {idx2_prefix}")
            popup.close()
        except Exception as e:
            # Popup didn't open — capture current page state as fallback
            for ext, fn in [
                ('.html', lambda pg=live: pg.content()),
                ('.txt',  lambda pg=live: pg.inner_text('body')),
            ]:
                try:
                    data = fn()
                    (out_dir / f"{idx2_prefix}{ext}").write_text(data, encoding='utf-8')
                    written.append(f"{idx2_prefix}{ext}")
                except Exception:
                    pass
            captures.append({'prefix': idx2_prefix, 'captcha': captcha_here, 'type': 'fallback', 'error': str(e)})
            print(f"  fallback saved → {idx2_prefix}  ({e})")


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
    args = ap.parse_args()

    queue = load_queue()
    if not queue:
        print("No tenancy records missing rent with a known SRO — nothing to do.")
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
    out_dir = SNAPSHOT_ROOT / f"{folder_ts}_{safe_label(args.output_label)}_bulk"
    out_dir.mkdir(parents=True, exist_ok=True)

    captures: list[dict] = []
    errors:   list[str]  = []
    written:  list[str]  = []

    print(f"\nSnapshot folder: {out_dir}")
    print(f"Browser opening. Navigate to the Document Number search tab on the IGR site.")
    print(f"For each doc: fill in SRO, Year, Doc No → solve CAPTCHA if shown → click Search.")
    print(f"Then press Enter here. Type 's' to skip a doc, 'done' to quit early.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page    = context.new_page()
        page.goto(args.url, timeout=60000, wait_until='domcontentloaded')

        for idx, r in enumerate(remaining):
            abs_num = args.skip + idx + 1
            total   = len(queue)

            print(f"┌── Doc {abs_num}/{total} ──────────────────────────────────────────")
            print(f"│  SRO     : {r['sro']}")
            print(f"│  Year    : {r['year']}")
            print(f"│  Doc No  : {r['doc']}")
            print(f"│  Flat    : {r['wing'] or '?'}  {r['unit']}  (registered {r['date']})")
            print(f"└───────────────────────────────────────────────────────────────────")

            try:
                cmd = input("  → Enter values in browser, press Enter when result loads  (s=skip  done=quit): ")
            except EOFError:
                break

            cmd = cmd.strip().lower()
            if cmd in ('done', 'q', 'quit', 'exit'):
                print("Stopping.")
                break
            if cmd == 's':
                print("  Skipped.\n")
                continue

            # Re-acquire live page reference
            page = next((pg for pg in context.pages if not pg.is_closed()), None)
            if page is None:
                print("  [ERROR] All browser pages closed — stopping.")
                break

            pause_if_captcha(page)

            # Files: capture_NNN_doc<docno>_<year>_r0.txt — matches ingest glob
            prefix = f"capture_{abs_num:03d}_doc{r['doc']}_{r['year']}"
            save_page(context, page, out_dir, prefix, written, captures)
            print()

        context.close()
        browser.close()

    metadata = {
        'capture_type': 'index2_targeted_docno',
        'url': args.url,
        'started_at': started_at,
        'method': 'playwright-guided-per-doc',
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
