#!/usr/bin/env python3
"""IGR free-search sweep over a CTS x year grid — script fills the form, human does CAPTCHA + paging.

For each (CTS number, year) the script:
  1) loads the free-search page fresh, selects district / village / year, types the CTS number
  2) stops — YOU solve the CAPTCHA and click Search (the script never touches the CAPTCHA)
  3) captures the results page + every IndexII popup on it
  4) stops again — YOU click the next page number, press Enter, it captures that page too
     (ASP.NET UpdatePanel pagination does not survive Playwright postbacks; kept human-operated,
      same as fetch_igr_index2_bulk.py)

Usage:
  python3 scripts/fetch_igr_cts_sweep.py --output-label ekta-tripolis --apply
  python3 scripts/fetch_igr_cts_sweep.py --cts "22A,22A/10" --years 2018-2026 --apply
  python3 scripts/fetch_igr_cts_sweep.py --self-check        # unit-check the grid expansion

Hard guards inherited from the other IGR scripts: host-locked, headed only, no CAPTCHA
bypass/OCR/solver, no DB writes. Snapshots are raw/untrusted and contain party PII.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PROJECT_ROOT / "exports" / "igr_cts_sweep"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from fetch_igr_esearch_playwright import (  # noqa: E402
    safe_label, redact_url, validate_url, detect_captcha,
)

DEFAULT_URL = "https://freesearchigrservice.maharashtra.gov.in/"
INDEX2_BTN_SEL = "input[value='IndexII']"

# Ekta Tripolis, per MahaRERA. Broad "22A" first, then each sub-plot; same for the 2601 series.
DEFAULT_CTS = ["22A", "22A/10", "22A/11A", "22A/14 PT", "2601", "2601/1"]

SEL = {
    "district":  "select#ddlDistrict",
    "village_tx": "input#txtAreaName",
    "village_dd": "select#ddlareaname",
    "year":      "select#ddlFromYear",
    "propno":    "input#txtAttributeValue",
    "search":    "input#btnMumbaisearch",
}


def expand_grid(cts_arg: str, years_arg: str) -> list[tuple[str, str]]:
    """'a,b' x '2020-2022,2024' -> [(a,2020),(a,2021),...]. Years descending, newest first."""
    cts = [c.strip() for c in cts_arg.split(",") if c.strip()] if cts_arg else list(DEFAULT_CTS)
    years: list[int] = []
    for part in (p.strip() for p in years_arg.split(",") if p.strip()):
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-", 1))
            years.extend(range(lo, hi + 1))
        else:
            years.append(int(part))
    years = sorted(set(years), reverse=True)
    return [(c, str(y)) for c in cts for y in years]


def _self_check() -> int:
    g = expand_grid("22A,2601", "2024-2026,2020")
    assert g[0] == ("22A", "2026") and g[3] == ("22A", "2020"), g[:4]
    assert len(g) == 8 and g[4][0] == "2601", g
    assert expand_grid("", "2026")[0][0] == "22A"
    print("self-check ok")
    return 0


def _fill(page, args, cts: str, year: str, timeout: int) -> list[str]:
    """Best-effort form fill. Returns list of problems (empty = fully filled)."""
    problems: list[str] = []

    try:
        page.select_option(SEL["district"], value=args.district_value)
        page.wait_for_timeout(1500)  # ASP.NET postback repopulates village
    except Exception as exc:  # noqa: BLE001
        problems.append(f"district: {exc}")

    try:
        page.fill(SEL["village_tx"], args.village_search)
        page.locator(SEL["village_tx"]).press("Tab")  # onchange -> __doPostBack
        page.wait_for_timeout(2500)
        opts = page.locator(f"{SEL['village_dd']} option").all_text_contents()
        want = args.village_option.lower()
        match = next((o for o in opts if want in o.lower()), None)
        if match:
            page.select_option(SEL["village_dd"], label=match)
            page.wait_for_timeout(800)
        else:
            problems.append(f"village option {args.village_option!r} not in {opts}")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"village: {exc}")

    for key, val in (("year", year), ("propno", cts)):
        try:
            if key == "year":
                page.select_option(SEL["year"], value=val)
            else:
                page.fill(SEL["propno"], val)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{key}: {exc}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="IGR CTS x year sweep (auto-fill, human CAPTCHA + paging).")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--output-label", default="cts-sweep")
    ap.add_argument("--cts", default="", help=f"comma list; default: {','.join(DEFAULT_CTS)}")
    ap.add_argument("--years", default="2010-2026", help="e.g. '2018-2026' or '2020,2024-2026'")
    ap.add_argument("--district-value", default="31", help="ddlDistrict value (31 = Mumbai Suburban)")
    ap.add_argument("--village-search", default="Pahadi", help="text typed into 'Enter Village Name'")
    ap.add_argument("--village-option", default="pahadi", help="substring of the village dropdown option")
    ap.add_argument("--building-label", default="Ekta Tripolis", help="provenance only")
    ap.add_argument("--timeout-ms", type=int, default=20000)
    ap.add_argument("--apply", action="store_true", help="actually open the browser")
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    if args.self_check:
        return _self_check()

    ok, host_or_msg = validate_url(args.url)
    if not ok:
        print(host_or_msg); return 1
    host = host_or_msg

    grid = expand_grid(args.cts, args.years)
    print(f"IGR CTS sweep. host={host}  label={args.output_label}  headed=ALWAYS")
    print(f"building={args.building_label!r}  district={args.district_value}  village~{args.village_option!r}")
    print(f"{len(grid)} searches: {len(set(c for c, _ in grid))} CTS x {len(set(y for _, y in grid))} years")
    print("Script fills the form only. You solve every CAPTCHA and click every page number.")

    if not args.apply:
        print("\nDry run. First 8 searches:")
        for c, y in grid[:8]:
            print(f"  {c:<12} {y}")
        print("Re-run with --apply to start.")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("Playwright not installed. Run: python3 -m playwright install chromium"); return 2

    from datetime import datetime, timezone
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    folder_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = SNAPSHOT_ROOT / f"{folder_ts}_{safe_label(args.output_label)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    captures: list[dict] = []
    errors: list[str] = []
    written: list[str] = []
    searches: list[dict] = []

    def _save(page_obj, tag: str) -> None:
        i = len(captures) + 1
        prefix = f"capture_{i:04d}_{safe_label(tag)}"
        captcha_here = detect_captcha(page_obj)
        for ext, fn in [(".png", lambda: page_obj.screenshot(path=str(out_dir / f"{prefix}.png"), full_page=True)),
                        (".html", lambda: (out_dir / f"{prefix}.html").write_text(page_obj.content(), encoding="utf-8")),
                        (".txt", lambda: (out_dir / f"{prefix}.txt").write_text(page_obj.inner_text("body"), encoding="utf-8"))]:
            try:
                fn(); written.append(f"{prefix}{ext}")
            except Exception:  # noqa: BLE001
                pass
        captures.append({"index": i, "tag": tag, "captcha_at_capture": captcha_here,
                         "url": redact_url(page_obj.url)})
        print(f"    saved #{i} {tag}")

    def _ask(prompt: str) -> str:
        try:
            return input(prompt).strip().lower()
        except EOFError:
            return "done"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            for qi, (cts, year) in enumerate(grid, 1):
                print(f"\n═══ [{qi}/{len(grid)}] CTS {cts}  year {year} ═══")
                try:
                    page.goto(args.url, timeout=args.timeout_ms * 3, wait_until="domcontentloaded")
                    page.wait_for_timeout(1200)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{cts}/{year}: page load: {exc}")
                    print(f"  [ERROR] page load: {exc}"); continue

                problems = _fill(page, args, cts, year, args.timeout_ms)
                for pr in problems:
                    print(f"  [fill] {pr} — fix it manually in the browser")

                print(f"  Form filled: district={args.district_value} village~{args.village_option} "
                      f"year={year} propno={cts}")
                print("  → In the BROWSER: solve the CAPTCHA and click Search. Wait for page-1 results.")
                cmd = _ask("  → then press Enter here ('skip' = next CTS/year, 'done' = end session): ")
                if cmd in ("done", "q", "quit", "exit"):
                    break
                if cmd == "skip":
                    searches.append({"cts": cts, "year": year, "pages": 0, "skipped": True}); continue

                pg_num = 0
                while True:
                    pg_num += 1
                    page = next((pg for pg in context.pages if not pg.is_closed()), None)
                    if page is None:
                        errors.append(f"{cts}/{year}: all pages closed"); break

                    print(f"  ── page {pg_num} ──")
                    _save(page, f"{cts}_{year}_p{pg_num}_results")

                    try:
                        page.wait_for_selector(INDEX2_BTN_SEL, timeout=args.timeout_ms)
                    except Exception:  # noqa: BLE001
                        pass
                    btn_count = page.locator(INDEX2_BTN_SEL).count()
                    print(f"    {btn_count} IndexII button(s)")

                    for row_idx in range(btn_count):
                        page = next((pg for pg in context.pages if not pg.is_closed()), None)
                        if page is None:
                            break
                        tag = f"{cts}_{year}_p{pg_num}_r{row_idx}"
                        try:
                            btn = page.locator(INDEX2_BTN_SEL).nth(row_idx)
                            with context.expect_page(timeout=args.timeout_ms) as popup_info:
                                btn.click()
                            popup = popup_info.value
                            try:
                                popup.wait_for_load_state("networkidle", timeout=args.timeout_ms)
                            except Exception:  # noqa: BLE001
                                pass
                            _save(popup, tag)
                            popup.close()
                        except Exception:  # noqa: BLE001
                            # Some rows render in-place instead of a popup.
                            try:
                                page.wait_for_load_state("networkidle", timeout=args.timeout_ms)
                            except Exception:  # noqa: BLE001
                                pass
                            _save(page, tag)
                            try:
                                page.go_back()
                                page.wait_for_load_state("networkidle", timeout=args.timeout_ms)
                            except Exception:  # noqa: BLE001
                                pass

                    print(f"    page {pg_num} done. In browser: click page {pg_num + 1} (or '...').")
                    cmd = _ask("  → Enter once it loads, 'next' = no more pages, 'done' = end session: ")
                    if cmd in ("done", "q", "quit", "exit"):
                        searches.append({"cts": cts, "year": year, "pages": pg_num})
                        raise KeyboardInterrupt
                    if cmd in ("next", "n"):
                        break

                searches.append({"cts": cts, "year": year, "pages": pg_num})

            context.close(); browser.close()
    except KeyboardInterrupt:
        print("\n  ended by operator")
    except Exception as exc:  # noqa: BLE001
        print(f"Fatal browser error: {exc}")
        errors.append(f"fatal: {exc}")

    metadata = {
        "capture_type": "igr_cts_sweep",
        "url": args.url, "host": host, "started_at": started_at,
        "method": "playwright-autofill-human-captcha-human-paging",
        "search_provenance": {
            "building_label": args.building_label,
            "district_value": args.district_value,
            "village_search": args.village_search, "village_option": args.village_option,
            "cts_list": sorted({c for c, _ in grid}), "years": sorted({y for _, y in grid}),
        },
        "planned_searches": len(grid),
        "searches_run": searches,
        "capture_count": len(captures),
        "error_count": len(errors),
        "captures": captures,
        "errors": errors,
        "files_written": written,
        "captcha_solved_by_human": True,
        "trusted_for_db": False,
        "human_review_required": True,
        "db_writes": False,
        "note": "Raw IGR Index II snapshots. Party PII; never committed; parse via review-gated parser only.",
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"\n── Done ──\nsnapshot folder : {out_dir}")
    print(f"searches run    : {len(searches)}/{len(grid)}")
    print(f"captures        : {len(captures)}   errors: {len(errors)}")
    for e in errors:
        print(f"  {e}")
    print("trusted_for_db=false  human_review_required=true  db_writes=false")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
