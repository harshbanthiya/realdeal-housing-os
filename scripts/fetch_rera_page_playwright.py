#!/usr/bin/env python3
"""Phase 6.10 guarded MahaRERA single-page browser capture (Playwright). Feasibility tool.

Opens EXACTLY ONE user-supplied MahaRERA URL with a headless (default) Chromium browser
and saves raw, UNTRUSTED snapshots (screenshot / HTML / visible text / network summary)
under the git-ignored exports/rera_snapshots/<timestamp>_<label>/ folder. It writes NOTHING
to the database, prints no page contents, and does only a single polite page load.

Hard guards: URL host must be maharerait.maharashtra.gov.in or maharera.maharashtra.gov.in;
exactly one URL; no form submission, no clicks, no downloads, no CAPTCHA/auth bypass. The
captured snapshot is raw evidence for later human review — metadata.json records
trusted_for_db=false and human_review_required=true. This script is the ONLY place in the
project allowed to make an external call, and only for one URL at a time.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PROJECT_ROOT / "exports" / "rera_snapshots"
ALLOWED_HOSTS = {"maharerait.maharashtra.gov.in", "maharera.maharashtra.gov.in"}


def safe_label(label: str) -> str:
    keep = [c if (c.isalnum() or c in "-_") else "-" for c in label]
    return "".join(keep)[:60] or "snapshot"


def validate_url(url: str) -> tuple[bool, str]:
    if not url:
        return False, "Refusing: --url is required."
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, f"Refusing: URL scheme {parsed.scheme!r} is not http/https."
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        return False, (f"Refusing: host {host!r} is not an allowed MahaRERA host "
                       f"({', '.join(sorted(ALLOWED_HOSTS))}).")
    return True, host


def main() -> int:
    parser = argparse.ArgumentParser(description="Guarded single-URL MahaRERA Playwright capture.")
    parser.add_argument("--url", default="", help="exactly one MahaRERA project URL")
    parser.add_argument("--output-label", required=True, help="short label for the snapshot folder")
    parser.add_argument("--timeout-ms", type=int, default=45000)
    headless = parser.add_mutually_exclusive_group()
    headless.add_argument("--headless", dest="headless", action="store_true", default=True)
    headless.add_argument("--headed", dest="headless", action="store_false")
    parser.add_argument("--save-html", action="store_true")
    parser.add_argument("--save-screenshot", action="store_true")
    parser.add_argument("--save-visible-text", action="store_true")
    parser.add_argument("--save-network-summary", action="store_true")
    parser.add_argument("--apply", action="store_true",
                        help="actually open the browser and fetch (omit for a dry-run plan)")
    args = parser.parse_args()

    ok, host_or_msg = validate_url(args.url)
    if not ok:
        print(host_or_msg)
        return 1
    host = host_or_msg

    # Default to the safest useful capture if nothing specific was requested.
    if not (args.save_html or args.save_screenshot or args.save_visible_text or args.save_network_summary):
        args.save_screenshot = True
        args.save_visible_text = True

    print(f"MahaRERA single-page capture. host={host}; label={args.output_label}; headless={args.headless}; "
          f"timeout_ms={args.timeout_ms}. One URL only; no forms/clicks/downloads; no CAPTCHA/auth bypass; "
          "no DB writes; snapshots are raw/untrusted.")
    requested = [n for n, v in [("screenshot", args.save_screenshot), ("html", args.save_html),
                                ("visible_text", args.save_visible_text), ("network_summary", args.save_network_summary)] if v]
    print(f"requested outputs: {', '.join(requested)}")

    if not args.apply:
        print("Dry run only (no browser opened, no external call). Re-run with --apply to perform the single fetch.")
        print(f"would write under: {SNAPSHOT_ROOT}/<timestamp>_{safe_label(args.output_label)}/")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("Refusing: Playwright is not installed. Install locally first:")
        print("  python3 -m pip install -r requirements-rera-fetch.txt")
        print("  python3 -m playwright install chromium")
        return 2

    # Timestamp comes from the OS clock at run time (kept out of import side effects).
    from datetime import datetime, timezone
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    folder_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = SNAPSHOT_ROOT / f"{folder_ts}_{safe_label(args.output_label)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    network: list[dict] = []
    written: list[str] = []
    status_code = None
    load_error = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=args.headless)
            context = browser.new_context()
            page = context.new_page()
            if args.save_network_summary:
                # Record only method + status + truncated URL; no bodies, no headers.
                page.on("response", lambda r: network.append(
                    {"method": r.request.method, "status": r.status, "url": r.url[:200]}))
            try:
                resp = page.goto(args.url, timeout=args.timeout_ms, wait_until="domcontentloaded")
                status_code = resp.status if resp else None
                page.wait_for_timeout(2500)  # let JS render; single polite settle, no looping
            except Exception as exc:  # noqa: BLE001 - report load problems, don't work around
                load_error = type(exc).__name__

            if args.save_screenshot:
                try:
                    page.screenshot(path=str(out_dir / "screenshot.png"), full_page=True)
                    written.append("screenshot.png")
                except Exception:  # noqa: BLE001
                    pass
            if args.save_html:
                try:
                    (out_dir / "page.html").write_text(page.content(), encoding="utf-8")
                    written.append("page.html")
                except Exception:  # noqa: BLE001
                    pass
            if args.save_visible_text:
                try:
                    text = page.inner_text("body")
                    (out_dir / "visible_text.txt").write_text(text, encoding="utf-8")
                    written.append("visible_text.txt")
                except Exception:  # noqa: BLE001
                    pass
            context.close()
            browser.close()
    except Exception as exc:  # noqa: BLE001 - e.g. missing chromium binary
        load_error = load_error or type(exc).__name__
        print(f"Browser/launch problem reported: {load_error}. Not working around it.")
        if "Executable doesn't exist" in str(exc) or "playwright install" in str(exc):
            print("Hint: run `python3 -m playwright install chromium` (downloads to the user cache, not the repo).")

    if args.save_network_summary:
        (out_dir / "network_summary.json").write_text(json.dumps(network, indent=2), encoding="utf-8")
        written.append("network_summary.json")

    metadata = {
        "url": args.url,
        "host": host,
        "fetched_at": fetched_at,
        "method": "playwright",
        "headless": args.headless,
        "http_status": status_code,
        "load_error": load_error,
        "external_call_made": True,
        "trusted_for_db": False,
        "human_review_required": True,
        "files_written": written,
        "network_events_captured": len(network),
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    written.append("metadata.json")

    # Print counts and PATHS only — never page contents.
    print(f"snapshot folder: {out_dir}")
    print(f"files written ({len(written)}): {', '.join(written)}")
    print(f"http_status={status_code}  load_error={load_error}  network_events={len(network)}")
    print("trusted_for_db=false  human_review_required=true  (raw untrusted snapshot; no DB write)")
    if load_error:
        print("NOTE: page load reported an error/block above. Reported as-is; no bypass attempted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
