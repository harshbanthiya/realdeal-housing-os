"""Targeted Index II capture — for a known doc_no, fetch just that document.

Complements fetch_igr_esearch_playwright.py (which captures full search sessions).
Use this when you already have a doc_no (e.g. from a staged search-result row) and
want to fetch only its Index II document from freeigrsearch.

Operator flow:
  1) Browser opens freeigrsearch free-search portal.
  2) Operator navigates to the Index II for the stated doc_no and solves CAPTCHA.
  3) Press Enter in THIS terminal to capture the document page.
  4) Type 'done' when finished.

Hard guards: same as fetch_igr_esearch_playwright.py — host-locked, headed only,
no CAPTCHA bypass, no DB writes, no auto-fill/auto-submit.
Snapshots written to git-ignored exports/igr_index2_snapshots/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PROJECT_ROOT / "exports" / "igr_index2_snapshots"

# ponytail: import shared guards/utils from sibling script (has __main__ guard, safe to import)
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from fetch_igr_esearch_playwright import (  # noqa: E402
    safe_label, redact_url, validate_url, detect_captcha, ALLOWED_HOSTS,
)

DEFAULT_URL = "https://freesearchigrservice.maharashtra.gov.in/"


def main() -> int:
    ap = argparse.ArgumentParser(description="Targeted IGR Index II capture for a known doc_no.")
    ap.add_argument("--url", default=DEFAULT_URL, help="IGR free-search URL (host-locked)")
    ap.add_argument("--doc-no", required=True, help="Document number to capture, e.g. '999/2026'")
    ap.add_argument("--year", default="", help="Registration year (provenance only)")
    ap.add_argument("--building-label", default="", help="Building this doc belongs to (provenance only)")
    ap.add_argument("--output-label", default="", help="Override snapshot folder label (default: doc_no)")
    ap.add_argument("--timeout-ms", type=int, default=60000)
    ap.add_argument("--apply", action="store_true", help="Actually open browser (omit = dry-run)")
    args = ap.parse_args()

    ok, host_or_msg = validate_url(args.url)
    if not ok:
        print(host_or_msg)
        return 1
    host = host_or_msg

    label = args.output_label or safe_label(f"index2_{args.doc_no}")
    print(f"IGR Index II targeted capture. host={host}; doc_no={args.doc_no!r}; headed=ALWAYS.")
    print(f"provenance: building={args.building_label!r} year={args.year!r}")
    print("Operator navigates to the document and solves CAPTCHA. No auto-fill, no bypass, no DB writes.")

    if not args.apply:
        print("\nDry run only — no browser opened. Re-run with --apply to start the session.")
        print(f"would write under: {SNAPSHOT_ROOT}/<timestamp>_{label}/")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("Refusing: Playwright not installed.")
        print("  python3 -m pip install -r requirements-rera-fetch.txt")
        print("  python3 -m playwright install chromium")
        return 2

    from datetime import datetime, timezone
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    folder_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = SNAPSHOT_ROOT / f"{folder_ts}_{label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    captures: list[dict] = []
    written: list[str] = []
    load_error = None

    def capture(tag: str) -> None:
        i = len(captures) + 1
        prefix = f"capture_{i:03d}_{safe_label(tag)}"
        captcha_here = detect_captcha(page)
        try:
            page.screenshot(path=str(out_dir / f"{prefix}.png"), full_page=True)
            written.append(f"{prefix}.png")
        except Exception:  # noqa: BLE001
            pass
        try:
            (out_dir / f"{prefix}.html").write_text(page.content(), encoding="utf-8")
            written.append(f"{prefix}.html")
        except Exception:  # noqa: BLE001
            pass
        try:
            (out_dir / f"{prefix}.txt").write_text(page.inner_text("body"), encoding="utf-8")
            written.append(f"{prefix}.txt")
        except Exception:  # noqa: BLE001
            pass
        captures.append({"index": i, "tag": tag, "captcha_present_at_capture": captcha_here,
                         "url_path": redact_url(page.url)})
        print(f"  captured #{i} ({tag}) — captcha_present={captcha_here}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            try:
                page.goto(args.url, timeout=args.timeout_ms, wait_until="domcontentloaded")
            except Exception as exc:  # noqa: BLE001
                load_error = type(exc).__name__

            print(f"\nBrowser open. Navigate to Index II for doc_no={args.doc_no!r}.")
            print("  Solve the CAPTCHA, open the document page, then press Enter here to capture.")
            print("  Type 'done' when finished.\n")

            rounds = 0
            while rounds < 10:  # ponytail: max 10 captures; one doc rarely needs more
                try:
                    cmd = input("Press Enter to capture (or tag), 'done' to finish: ")
                except EOFError:
                    break
                if cmd.strip().lower() in ("done", "q", "quit", "exit"):
                    break
                tag = cmd.strip() or f"index2_{rounds + 1}"
                capture(tag)
                rounds += 1

            context.close()
            browser.close()
    except Exception as exc:  # noqa: BLE001
        load_error = load_error or type(exc).__name__
        print(f"Browser error: {load_error}")

    any_captcha = any(c["captcha_present_at_capture"] for c in captures)
    metadata = {
        "capture_type": "index2",
        "doc_no": args.doc_no,
        "url": args.url,
        "host": host,
        "started_at": started_at,
        "method": "playwright-human-driven",
        "headless": False,
        "search_provenance": {"building_label": args.building_label, "year": args.year},
        "load_error": load_error,
        "captures": captures,
        "capture_count": len(captures),
        "captcha_solved_by_human": (len(captures) > 0 and not any_captcha),
        "captcha_present_at_some_capture": any_captcha,
        "external_call_made": True,
        "trusted_for_db": False,
        "human_review_required": True,
        "db_writes": False,
        "files_written": written,
        "note": "Raw IGR Index II snapshot. Contains party PII; never committed; parse via review-gated parser only.",
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    written.append("metadata.json")

    print(f"\nsnapshot folder: {out_dir}")
    print(f"captures: {len(captures)}  files: {len(written)}")
    print(f"captcha_solved_by_human={metadata['captcha_solved_by_human']}  trusted_for_db=false")
    if not captures:
        print("No pages captured. Snapshot folder contains only metadata.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
