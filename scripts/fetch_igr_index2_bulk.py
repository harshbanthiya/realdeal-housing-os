#!/usr/bin/env python3
"""Bulk IGR Index II capture — operator navigates each page, script captures everything.

ASP.NET UpdatePanel pagination does not work from Playwright (postbacks bounce to page 1).
This script uses human-in-loop navigation: you click each page in the browser,
press Enter here to capture it, then move to the next page.

Operator flow:
  1) Browser opens. Fill form, solve CAPTCHA, click Search — wait for page-1 results.
  2) Press Enter in THIS terminal — script captures all IndexII on the current page.
  3) In the browser, click the next page number (or '...' to jump to a new group).
  4) Press Enter again. Repeat until all pages captured.
  5) Type 'done' when finished.

Hard guards: host-locked, headed only, no CAPTCHA bypass, no auto-fill, no DB writes.
Snapshots written to exports/igr_index2_snapshots/<ts>_<label>_bulk/ (git-ignored).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PROJECT_ROOT / "exports" / "igr_index2_snapshots"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from fetch_igr_esearch_playwright import (  # noqa: E402
    safe_label, redact_url, validate_url, detect_captcha,
)

DEFAULT_URL = "https://freesearchigrservice.maharashtra.gov.in/"
INDEX2_BTN_SEL = "input[value='IndexII']"


def main() -> int:
    ap = argparse.ArgumentParser(description="Bulk IGR Index II capture (auto-paginate, single CAPTCHA session).")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--output-label", required=True)
    ap.add_argument("--year",     default="", help="provenance only")
    ap.add_argument("--building-label", default="", help="provenance only")
    ap.add_argument("--timeout-ms", type=int, default=20000)
    ap.add_argument("--apply", action="store_true", help="actually open browser")
    args = ap.parse_args()

    ok, host_or_msg = validate_url(args.url)
    if not ok:
        print(host_or_msg); return 1
    host = host_or_msg

    print(f"IGR Index II BULK capture. host={host}; label={args.output_label}; headed=ALWAYS.")
    print(f"provenance: building={args.building_label!r} year={args.year!r}")
    print("Operator solves CAPTCHA once. No auto-fill, no bypass, no DB writes.")

    if not args.apply:
        print("\nDry run — no browser opened. Re-run with --apply to start.")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("Playwright not installed. Run: python3 -m playwright install chromium"); return 2

    from datetime import datetime, timezone
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    folder_ts  = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = SNAPSHOT_ROOT / f"{folder_ts}_{safe_label(args.output_label)}_bulk"
    out_dir.mkdir(parents=True, exist_ok=True)

    captures: list[dict] = []
    errors:   list[str]  = []
    written:  list[str]  = []
    pg_num = 0

    def _save(page_obj, tag: str) -> None:
        i = len(captures) + 1
        prefix = f"capture_{i:03d}_{safe_label(tag)}"
        captcha_here = detect_captcha(page_obj)
        for ext, fn in [(".png", lambda: page_obj.screenshot(path=str(out_dir / f"{prefix}.png"), full_page=True)),
                        (".html", lambda: (out_dir / f"{prefix}.html").write_text(page_obj.content(), encoding="utf-8")),
                        (".txt",  lambda: (out_dir / f"{prefix}.txt").write_text(page_obj.inner_text("body"), encoding="utf-8"))]:
            try:
                fn(); written.append(f"{prefix}{ext}")
            except Exception:  # noqa: BLE001
                pass
        captures.append({"index": i, "tag": tag, "captcha_at_capture": captcha_here,
                         "url": redact_url(page_obj.url)})
        print(f"  saved #{i} {tag}  captcha={captcha_here}")

    def _pause_if_captcha(page_obj) -> None:
        if detect_captcha(page_obj):
            print("\n*** CAPTCHA detected — solve it in the browser then press Enter here ***")
            try:
                input("(press Enter after solving CAPTCHA): ")
            except EOFError:
                pass

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page    = context.new_page()
            page.goto(args.url, timeout=args.timeout_ms * 3, wait_until="domcontentloaded")

            print("\nBrowser open. Fill form → solve CAPTCHA → click Search → wait for page-1 results.")
            print("Then press Enter here to start capturing. Type 'done' when all pages are captured.\n")
            try:
                cmd = input("Press Enter when page-1 is visible (or 'done' to exit): ")
            except EOFError:
                print("(no stdin — ending)"); browser.close(); return 1
            if cmd.strip().lower() in ("done", "q", "quit", "exit"):
                browser.close(); return 0

            _pause_if_captcha(page)

            pg_num = 0
            while True:
                pg_num += 1

                # Re-acquire live page reference (popup cycles can leave stale ref)
                page = next((p for p in context.pages if not p.is_closed()), None)
                if page is None:
                    print("  [ERROR] all pages closed — ending"); break

                _pause_if_captcha(page)

                print(f"\n── Page {pg_num} ──")

                # Capture the results list page itself before opening any IndexII
                _save(page, f"p{pg_num}_results")

                try:
                    page.wait_for_selector(INDEX2_BTN_SEL, timeout=args.timeout_ms)
                except Exception:  # noqa: BLE001
                    pass
                btn_count = page.locator(INDEX2_BTN_SEL).count()
                print(f"  {btn_count} IndexII button(s)")

                for row_idx in range(btn_count):
                    page = next((p for p in context.pages if not p.is_closed()), None)
                    if page is None:
                        print("  [ERROR] all pages closed — ending session"); break

                    tag = f"p{pg_num}_r{row_idx}"
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

                # Ask operator to navigate to the next page
                print(f"\n  Page {pg_num} done ({btn_count} IndexII captured).")
                print(f"  In browser: click page {pg_num + 1} (or '...' if not visible).")
                try:
                    cmd = input("  Press Enter when next page is loaded, or type 'done' to finish: ")
                except EOFError:
                    break
                if cmd.strip().lower() in ("done", "q", "quit", "exit"):
                    break

            context.close()
            browser.close()

    except Exception as exc:  # noqa: BLE001
        print(f"Fatal browser error: {exc}")
        errors.append(f"fatal: {exc}")

    metadata = {
        "capture_type": "index2_bulk",
        "url": args.url, "host": host, "started_at": started_at,
        "method": "playwright-bulk-auto-paginate",
        "search_provenance": {"building_label": args.building_label, "year": args.year},
        "total_result_pages_captured": pg_num,
        "capture_count": len(captures),
        "error_count": len(errors),
        "captures": captures,
        "errors": errors,
        "files_written": written,
        "captcha_solved_by_human": True,  # operator solved at start (and any mid-run pauses)
        "trusted_for_db": False,
        "human_review_required": True,
        "db_writes": False,
        "note": "Bulk Index II snapshots. Contains party PII; never committed; parse via review-gated parser only.",
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    written.append("metadata.json")

    print(f"\n── Done ──")
    print(f"snapshot folder : {out_dir}")
    print(f"captures        : {len(captures)}")
    print(f"errors          : {len(errors)}")
    if errors:
        for e in errors:
            print(f"  {e}")
    print("trusted_for_db=false  human_review_required=true  db_writes=false")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
