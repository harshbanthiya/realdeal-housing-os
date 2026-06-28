#!/usr/bin/env python3
"""Test script: auto-fill IGR free-search form by document number, wait for human CAPTCHA.

Runs ONE record from the IH missing-tenancy queue. Fills SRO + Year + Doc No,
then PAUSES so the operator can solve the CAPTCHA and press Enter. After Enter,
auto-clicks Search, waits for results, clicks IndexII, saves the popup.

Findings from this test go back into fetch_igr_docno_targeted.py --autofill.

Usage:
  python scripts/test_igr_prefill.py                        # first queued doc
  python scripts/test_igr_prefill.py --doc 9701 --sro "Joint S.R. Mumbai 18" --year 2024
  python scripts/test_igr_prefill.py --dry-run              # print selectors found, no interact
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from _db import run_psql

DEFAULT_URL = "https://freesearchigrservice.maharashtra.gov.in/"
INDEX2_BTN_SEL = "input[value='IndexII']"
IH_BLDG_ID = "0e72db71-8b93-4ecd-879c-17d8d8f2b206"

# IGR free-search form selectors (document-number tab).
# Discovered by inspection; the site uses ASP.NET WebForms naming conventions.
# If a selector fails, the script falls back to printing and waiting for manual entry.
FORM_SELECTORS = {
    # Tab that activates the doc-number search form
    "doc_number_tab": [
        "a[href*='DocNo']", "a[href*='docno' i]", "a[href*='DocumentNumber' i]",
        "li:has(a[href*='DocNo'])", "#tab3", "#tabDocumentNumber",
    ],
    # SRO / office name dropdown
    "sro_select": [
        "select#ddlSROName", "select[name*='SROName' i]", "select[id*='sro' i]",
        "select[name*='sro' i]", "select[id*='Office' i]",
    ],
    # Registration year
    "year_input": [
        "input#txtYear", "input[name*='Year' i]", "select#ddlYear",
        "select[name*='Year' i]", "input[id*='year' i]",
    ],
    # Document number
    "docno_input": [
        "input#txtDocumentNo", "input[name*='DocumentNo' i]", "input[id*='DocNo' i]",
        "input[name*='DocNo' i]", "input[id*='document' i]",
    ],
    # CAPTCHA text input
    "captcha_input": [
        "input#txtCaptcha", "input[name*='Captcha' i]", "input[id*='captcha' i]",
    ],
    # Search / submit button
    "search_btn": [
        "input#btnSearch", "input[value='Search' i]", "button[type='submit']",
        "input[type='submit']",
    ],
}


def load_one(doc: str | None, sro: str | None, year: str | None) -> dict:
    """Load the first missing IH L&L record (or the specific one requested)."""
    sro_clause = f"AND r.sro_office ILIKE '%{sro}%'" if sro else ""
    doc_clause = f"AND r.doc_number = '{doc}'" if doc else ""
    _, out = run_psql(f"""
        SELECT
            r.doc_number,
            r.sro_office,
            COALESCE(EXTRACT(year FROM r.registration_date)::int, r.registration_year)::int AS reg_year,
            COALESCE(bu.wing, r.wing_text, '') AS wing,
            COALESCE(bu.unit_number, r.unit_text, '') AS unit
        FROM unit_registration_records r
        JOIN buildings b ON b.id = r.building_id
        LEFT JOIN building_units bu ON bu.id = r.building_unit_id
        WHERE b.id = '{IH_BLDG_ID}'
          AND r.transaction_category = 'tenancy'
          AND (r.tenancy_monthly_rent IS NULL OR r.tenancy_end_date IS NULL)
          AND r.doc_number NOT LIKE 'SAMPLE%%'
          AND r.sro_office IS NOT NULL AND r.sro_office != ''
          {sro_clause}
          {doc_clause}
        ORDER BY r.sro_office, r.registration_date, r.doc_number::int
        LIMIT 1
    """)
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 5:
            return {
                'doc': parts[0], 'sro': parts[1],
                'year': year or parts[2],
                'wing': parts[3], 'unit': parts[4],
            }
    return {}


def first_match(page, selectors: list[str], timeout: int = 3000):
    """Return the first selector that finds an element, or None."""
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                return sel, loc.first
        except Exception:
            pass
    return None, None


_CAPTCHA_SELS = (
    "input[name*='captcha' i]", "input[id*='captcha' i]",
    "img[src*='captcha' i]", "img[id*='captcha' i]", "[class*='captcha' i]",
)
_CAPTCHA_WORDS = ("captcha", "enter the characters", "enter the text", "type the code")

def detect_captcha(page) -> bool:
    try:
        for sel in _CAPTCHA_SELS:
            if page.locator(sel).count() > 0:
                return True
        body = page.inner_text("body").lower()[:2000]
        return any(w in body for w in _CAPTCHA_WORDS)
    except Exception:
        return False


def prefill_form(page, r: dict, dry_run: bool = False) -> dict[str, str]:
    """Try to fill the doc-number search form. Returns dict of what worked."""
    result: dict[str, str] = {}

    # --- 1. Activate the doc-number tab ---
    tab_sel, tab_el = first_match(page, FORM_SELECTORS["doc_number_tab"])
    if tab_el and not dry_run:
        try:
            tab_el.click()
            page.wait_for_timeout(500)
            print(f"  [tab] clicked: {tab_sel}")
        except Exception as e:
            print(f"  [tab] click failed ({tab_sel}): {e}")
    elif tab_sel:
        print(f"  [tab] found: {tab_sel}")
    else:
        print("  [tab] not found — may already be on doc-number tab or page structure differs")

    # --- 2. SRO select ---
    sro_sel, sro_el = first_match(page, FORM_SELECTORS["sro_select"])
    if sro_el:
        result["sro_selector"] = sro_sel
        if not dry_run:
            # Try to select by label text (partial match, case-insensitive)
            sro_name = r["sro"]
            try:
                # Playwright select_option tries: value, label, index
                # Use label with partial text via JS
                options = page.evaluate(f"""
                    () => Array.from(document.querySelector('{sro_sel}')?.options || [])
                        .map(o => ({{v: o.value, t: o.text}}))
                        .filter(o => o.t.toLowerCase().includes('{sro_name[:15].lower()}'))
                """)
                if options:
                    best = options[0]
                    sro_el.select_option(value=best['v'])
                    print(f"  [sro] selected: {best['t']!r} (value={best['v']!r})")
                    result["sro_matched"] = best['t']
                else:
                    print(f"  [sro] no option matching {sro_name!r} — select manually")
                    result["sro_matched"] = "manual"
            except Exception as e:
                print(f"  [sro] select failed: {e}")
    else:
        print(f"  [sro] dropdown not found — tried: {FORM_SELECTORS['sro_select']}")

    # --- 3. Year ---
    yr_sel, yr_el = first_match(page, FORM_SELECTORS["year_input"])
    if yr_el:
        result["year_selector"] = yr_sel
        if not dry_run:
            try:
                if yr_el.evaluate("e => e.tagName") == "SELECT":
                    yr_el.select_option(str(r["year"]))
                else:
                    yr_el.triple_click()
                    yr_el.type(str(r["year"]))
                print(f"  [year] filled: {r['year']!r}")
            except Exception as e:
                print(f"  [year] fill failed: {e}")
    else:
        print(f"  [year] field not found — tried: {FORM_SELECTORS['year_input']}")

    # --- 4. Doc number ---
    doc_sel, doc_el = first_match(page, FORM_SELECTORS["docno_input"])
    if doc_el:
        result["docno_selector"] = doc_sel
        if not dry_run:
            try:
                doc_el.triple_click()
                doc_el.type(str(r["doc"]))
                print(f"  [docno] filled: {r['doc']!r}")
            except Exception as e:
                print(f"  [docno] fill failed: {e}")
    else:
        print(f"  [docno] field not found — tried: {FORM_SELECTORS['docno_input']}")

    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", help="Specific doc number to test")
    ap.add_argument("--sro", help="SRO name filter")
    ap.add_argument("--year", help="Override year")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--dry-run", action="store_true", help="Open page, probe selectors, no fill/click")
    ap.add_argument("--output-dir", help="Where to save snapshots (default: exports/igr_test_prefill/)")
    args = ap.parse_args()

    r = load_one(args.doc, args.sro, args.year)
    if not r:
        print("No matching queue record found.")
        return 1

    print(f"\nTest record:")
    print(f"  SRO    : {r['sro']}")
    print(f"  Year   : {r['year']}")
    print(f"  Doc No : {r['doc']}")
    print(f"  Flat   : {r['wing']} {r['unit']}")

    if args.dry_run:
        print("\nDry-run: will open browser and probe form selectors only (no fill).")

    out_dir = Path(args.output_dir) if args.output_dir else (
        PROJECT_ROOT / "exports" / "igr_test_prefill"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("Playwright not installed.  Run: python3 -m playwright install chromium")
        return 2

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()

        print(f"\nOpening: {args.url}")
        page.goto(args.url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        print("\nProbing form selectors...")
        fill_result = prefill_form(page, r, dry_run=args.dry_run)

        # --- 5. CAPTCHA pause ---
        if not args.dry_run:
            cap = detect_captcha(page)
            if cap:
                print("\n  *** CAPTCHA detected ***")
                print("  1. Solve the CAPTCHA in the browser window.")
                print("  2. Press Enter here when done (the script will click Search).")
            else:
                print("\n  No CAPTCHA detected yet. If it appears after filling, solve it.")
                print("  Press Enter when ready to click Search.")
            try:
                input("\n  → Press Enter to click Search (or Ctrl-C to quit): ")
            except (EOFError, KeyboardInterrupt):
                print("Aborted.")
                browser.close()
                return 0

            # --- 6. Click Search ---
            search_sel, search_el = first_match(page, FORM_SELECTORS["search_btn"])
            if search_el:
                print(f"  [search] clicking: {search_sel}")
                search_el.click()
                page.wait_for_timeout(3000)
            else:
                print("  [search] button not found — check form after CAPTCHA, click manually")
                print("  Press Enter when results are loaded.")
                try:
                    input("  → Press Enter when results page loaded: ")
                except (EOFError, KeyboardInterrupt):
                    pass

            # --- 7. Save results page ---
            prefix = f"doc{r['doc']}_{r['year']}"
            for ext, fn in [
                (".html", lambda: page.content()),
                (".txt", lambda: page.inner_text("body")),
            ]:
                try:
                    data = fn()
                    (out_dir / f"{prefix}_results{ext}").write_text(data, encoding="utf-8")
                    print(f"  [saved] {prefix}_results{ext}")
                except Exception as e:
                    print(f"  [save] {ext} failed: {e}")

            # --- 8. Click IndexII buttons ---
            try:
                page.wait_for_selector(INDEX2_BTN_SEL, timeout=10000)
            except Exception:
                print("  [IndexII] no button found within 10s")

            btn_count = page.locator(INDEX2_BTN_SEL).count()
            print(f"  [IndexII] {btn_count} button(s) found")

            for i in range(btn_count):
                try:
                    live = next((pg for pg in ctx.pages if not pg.is_closed()), None)
                    if not live:
                        break
                    btn = live.locator(INDEX2_BTN_SEL).nth(i)
                    with ctx.expect_page(timeout=15000) as popup_info:
                        btn.click()
                    popup = popup_info.value
                    popup.wait_for_load_state("networkidle", timeout=15000)
                    idx_prefix = f"{prefix}_r{i}"
                    for ext, fn in [
                        (".html", lambda pg=popup: pg.content()),
                        (".txt", lambda pg=popup: pg.inner_text("body")),
                    ]:
                        try:
                            data = fn()
                            (out_dir / f"{idx_prefix}{ext}").write_text(data, encoding="utf-8")
                            print(f"  [saved] IndexII → {idx_prefix}{ext}")
                        except Exception as e:
                            print(f"  [save] IndexII {ext} failed: {e}")
                    popup.close()
                except Exception as e:
                    print(f"  [IndexII] button {i} failed: {e}")

        # Save probe results
        probe = {**fill_result, "dry_run": args.dry_run, "record": r}
        (out_dir / "probe.json").write_text(json.dumps(probe, indent=2), encoding="utf-8")
        print(f"\nProbe results → {out_dir / 'probe.json'}")
        print(f"Snapshots → {out_dir}/")

        ctx.close()
        browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
