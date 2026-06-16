#!/usr/bin/env python3
"""Phase 6.18 guarded IGR eSearch capture (Playwright, human-driven, human CAPTCHA).

Opens the Maharashtra IGR "free search" portal (freesearchigrservice.maharashtra.gov.in) in a
HEADED browser so a HUMAN can: pick year / district / tahsil / village, enter the property
(CTS/survey) number, SOLVE THE CAPTCHA, click Search, and open each Index II. The script captures
raw, UNTRUSTED snapshots (screenshot / HTML / visible text / network summary) ON OPERATOR COMMAND
(press Enter to capture the current page; type 'done' to finish) under the git-ignored
exports/igr_snapshots/<timestamp>_<label>/ folder.

It writes NOTHING to the database, prints no page contents and no CAPTCHA/party text, and does
NOT auto-fill-and-submit the search: the operator drives every query and solves every CAPTCHA. The
script never reads, OCRs, solves, auto-submits, or uses a service for the CAPTCHA. There is no
crawling/looping over many properties — one operator-driven session, capture-on-Enter only.

Hard guards: host must be freesearchigrservice.maharashtra.gov.in; headed only; no CAPTCHA/auth
bypass; no OCR; no solving services; no DB writes; bounded capture count. metadata.json records
trusted_for_db=false, human_review_required=true, captcha_solved_by_human (operator-attested).
This is the IGR analogue of fetch_rera_page_playwright.py (the MahaRERA capture).

Snapshots contain personal party names (public register, but PII) — exports/ is git-ignored and
these are never committed; they stay raw/untrusted until the review-gated Index II parser runs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PROJECT_ROOT / "exports" / "igr_snapshots"
ALLOWED_HOSTS = {"freesearchigrservice.maharashtra.gov.in"}
DEFAULT_URL = "https://freesearchigrservice.maharashtra.gov.in/"

MAX_BODY_FILES = 25
MAX_BODY_BYTES = 512 * 1024

CAPTCHA_TEXT_SIGNALS = (
    "captcha", "enter the characters", "enter the text shown", "type the code",
    "i'm not a robot", "verify you are human",
)
CAPTCHA_SELECTORS = (
    "input[name*='captcha' i]", "input[id*='captcha' i]",
    "img[src*='captcha' i]", "img[id*='captcha' i]", "[class*='captcha' i]",
)


def safe_label(label: str) -> str:
    keep = [c if (c.isalnum() or c in "-_") else "-" for c in label]
    return "".join(keep)[:60] or "igr"


def redact_url(url: str) -> str:
    try:
        p = urlparse(url)
        path = (p.path or "")[:160]
        base = f"{p.scheme}://{p.hostname}{path}"
        if p.query:
            base += "?[redacted-query]"
        return base
    except Exception:  # noqa: BLE001
        return "[unparseable-url]"


def validate_url(url: str) -> tuple[bool, str]:
    if not url:
        return False, "Refusing: --url is required."
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, f"Refusing: URL scheme {parsed.scheme!r} is not http/https."
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        return False, f"Refusing: host {host!r} is not the allowed IGR host ({', '.join(sorted(ALLOWED_HOSTS))})."
    return True, host


def detect_captcha(page) -> bool:
    try:
        body = (page.inner_text("body") or "").lower()
    except Exception:  # noqa: BLE001
        body = ""
    if any(sig in body for sig in CAPTCHA_TEXT_SIGNALS):
        return True
    for sel in CAPTCHA_SELECTORS:
        try:
            if page.locator(sel).count() > 0:
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Guarded human-driven IGR eSearch Playwright capture.")
    parser.add_argument("--url", default=DEFAULT_URL, help="IGR free-search URL (host-locked)")
    parser.add_argument("--output-label", required=True, help="short label for the snapshot folder")
    # Search parameters — recorded into metadata for provenance; the OPERATOR enters them in the form.
    parser.add_argument("--year", default="", help="registration year being searched (provenance only)")
    parser.add_argument("--district", default="", help="district, e.g. 'Mumbai Suburban' (provenance only)")
    parser.add_argument("--village", default="", help="village/tahsil, e.g. 'Pahadi' (provenance only)")
    parser.add_argument("--cts", default="", help="property/CTS/survey number, e.g. '260/5A' (provenance only)")
    parser.add_argument("--building-label", default="", help="which building this search is for (provenance only)")

    parser.add_argument("--timeout-ms", type=int, default=60000)
    parser.add_argument("--max-captures", type=int, default=40, help="safety bound on capture-on-Enter rounds")

    # Output toggles (default: the safe, useful set).
    parser.add_argument("--save-html", action="store_true")
    parser.add_argument("--save-screenshot", action="store_true")
    parser.add_argument("--save-visible-text", action="store_true")
    parser.add_argument("--save-network-summary", action="store_true")
    parser.add_argument("--save-response-bodies", action="store_true",
                        help="save same-host JSON/HTML response bodies (query strings redacted)")

    parser.add_argument("--apply", action="store_true",
                        help="actually open the browser (omit for a dry-run plan; no external call)")
    args = parser.parse_args()

    ok, host_or_msg = validate_url(args.url)
    if not ok:
        print(host_or_msg)
        return 1
    host = host_or_msg

    if not (args.save_html or args.save_screenshot or args.save_visible_text
            or args.save_network_summary or args.save_response_bodies):
        args.save_screenshot = True
        args.save_visible_text = True
        args.save_html = True
        args.save_network_summary = True

    print(f"IGR eSearch human-driven capture. host={host}; label={args.output_label}; headed=ALWAYS.")
    print(f"search provenance: building={args.building_label!r} year={args.year!r} "
          f"district={args.district!r} village={args.village!r} cts={args.cts!r}")
    print("Operator drives every query and solves every CAPTCHA. No auto-fill/auto-submit, no CAPTCHA "
          "bypass/OCR/solver, no crawl/loop, no DB writes. Snapshots are raw/untrusted (contain PII).")

    if not args.apply:
        print("Dry run only (no browser opened, no external call). Re-run with --apply to start the session.")
        print(f"would write under: {SNAPSHOT_ROOT}/<timestamp>_{safe_label(args.output_label)}/")
        print("In the session: enter the search in the form, solve the CAPTCHA, click Search; then press")
        print("Enter here to capture the results page, open each Index II and press Enter to capture it,")
        print("and type 'done' when finished.")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("Refusing: Playwright is not installed. Install locally first:")
        print("  python3 -m pip install -r requirements-rera-fetch.txt")
        print("  python3 -m playwright install chromium")
        return 2

    from datetime import datetime, timezone
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    folder_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = SNAPSHOT_ROOT / f"{folder_ts}_{safe_label(args.output_label)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    req_count = {"n": 0}
    responses: list[dict] = []
    saved_bodies: list[dict] = []
    written: list[str] = []
    captures: list[dict] = []
    load_error = None

    def on_request(_req):
        req_count["n"] += 1

    def on_response(r):
        try:
            ctype = (r.headers.get("content-type", "") or "").lower()
        except Exception:  # noqa: BLE001
            ctype = ""
        try:
            rhost = (urlparse(r.url).hostname or "").lower()
        except Exception:  # noqa: BLE001
            rhost = ""
        same_host = rhost == host
        json_like = "json" in ctype or r.url.lower().split("?")[0].endswith(".json")
        html_like = "html" in ctype
        try:
            status = r.status
        except Exception:  # noqa: BLE001
            status = None
        responses.append({"same_host": same_host, "json_like": json_like, "html_like": html_like,
                          "status": status, "path": redact_url(r.url)})
        if (args.save_response_bodies and same_host and (json_like or html_like)
                and len(saved_bodies) < MAX_BODY_FILES):
            try:
                body = r.body()
            except Exception:  # noqa: BLE001
                return
            if not body or len(body) > MAX_BODY_BYTES:
                return
            idx = len(saved_bodies) + 1
            ext = "json" if json_like else "html"
            try:
                (out_dir / f"response_body_{idx:03d}.{ext}").write_bytes(body)
                saved_bodies.append({"idx": idx, "ext": ext})
            except Exception:  # noqa: BLE001
                return

    def capture(tag: str) -> None:
        i = len(captures) + 1
        prefix = f"capture_{i:03d}_{safe_label(tag)}"
        captcha_here = detect_captcha(page)
        if args.save_screenshot:
            try:
                page.screenshot(path=str(out_dir / f"{prefix}.png"), full_page=True)
                written.append(f"{prefix}.png")
            except Exception:  # noqa: BLE001
                pass
        if args.save_html:
            try:
                (out_dir / f"{prefix}.html").write_text(page.content(), encoding="utf-8")
                written.append(f"{prefix}.html")
            except Exception:  # noqa: BLE001
                pass
        if args.save_visible_text:
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
            browser = p.chromium.launch(headless=False)  # headed ALWAYS: human solves CAPTCHA
            context = browser.new_context()
            page = context.new_page()
            page.on("request", on_request)
            page.on("response", on_response)

            try:
                page.goto(args.url, timeout=args.timeout_ms, wait_until="domcontentloaded")
            except Exception as exc:  # noqa: BLE001
                load_error = type(exc).__name__

            print("\nBrowser is open. In the WINDOW:")
            print("  1) Choose year / district / tahsil / village and enter the property (CTS) number.")
            print("  2) SOLVE THE CAPTCHA yourself and click Search.")
            print("  3) Back HERE: press Enter to capture the results page.")
            print("  4) Open each Index II in the window, press Enter here to capture each.")
            print("  5) Type 'done' (or 'q') when finished.\n")

            rounds = 0
            while rounds < args.max_captures:
                try:
                    cmd = input("Press Enter to capture current page (or type a short tag), 'done' to finish: ")
                except EOFError:
                    print("  (no interactive stdin; ending session without capture)")
                    break
                if cmd.strip().lower() in ("done", "q", "quit", "exit"):
                    break
                tag = cmd.strip() or ("results" if not captures else f"index2_{len(captures)}")
                capture(tag)
                rounds += 1
            if rounds >= args.max_captures:
                print(f"  reached --max-captures={args.max_captures}; ending session.")

            context.close()
            browser.close()
    except Exception as exc:  # noqa: BLE001
        load_error = load_error or type(exc).__name__
        print(f"Browser/launch problem reported: {load_error}. Not working around it.")
        if "Executable doesn't exist" in str(exc) or "playwright install" in str(exc):
            print("Hint: run `python3 -m playwright install chromium` (downloads to the user cache, not the repo).")

    total_responses = len(responses)
    same_host = sum(1 for r in responses if r["same_host"])
    json_like = sum(1 for r in responses if r["json_like"])
    html_like = sum(1 for r in responses if r["html_like"])
    failed_resp = sum(1 for r in responses if (r["status"] or 0) >= 400)
    candidate_eps = sorted({r["path"] for r in responses if r["same_host"] and r["json_like"]})
    network_summary = {
        "total_requests": req_count["n"],
        "total_responses": total_responses,
        "same_host_responses": same_host,
        "json_like_responses": json_like,
        "html_responses": html_like,
        "failed_responses": failed_resp,
        "candidate_endpoint_count": len(candidate_eps),
        "candidate_endpoints": candidate_eps[:50],
        "note": "counts only; no cookies/auth/headers/tokens stored; query strings redacted",
    }
    if args.save_network_summary:
        (out_dir / "network_summary.json").write_text(json.dumps(network_summary, indent=2), encoding="utf-8")
        written.append("network_summary.json")

    any_captcha_during = any(c["captcha_present_at_capture"] for c in captures)
    metadata = {
        "url": args.url,
        "host": host,
        "started_at": started_at,
        "method": "playwright-human-driven",
        "headless": False,
        "search_provenance": {
            "building_label": args.building_label, "year": args.year,
            "district": args.district, "village": args.village, "cts": args.cts,
        },
        "load_error": load_error,
        "captures": captures,
        "capture_count": len(captures),
        # The operator solved any CAPTCHA themselves; the script never did. If every capture was
        # taken with no CAPTCHA gate visible on a results/Index-II page, the human had cleared it.
        "captcha_solved_by_human": (len(captures) > 0 and not any_captcha_during),
        "captcha_present_at_some_capture": any_captcha_during,
        "external_call_made": True,
        "trusted_for_db": False,
        "human_review_required": True,
        "db_writes": False,
        "files_written": written,
        "network_events_captured": total_responses,
        "note": "Raw IGR Index II snapshot(s). Contains party PII; never committed; parse only via the review-gated Index II parser.",
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    written.append("metadata.json")

    print(f"\nsnapshot folder: {out_dir}")
    print(f"captures: {len(captures)}  files written: {len(written)}")
    print(f"network: requests={req_count['n']} responses={total_responses} same_host={same_host} "
          f"json_like={json_like} candidate_endpoints={len(candidate_eps)}")
    print(f"captcha_solved_by_human={metadata['captcha_solved_by_human']}  "
          f"captcha_present_at_some_capture={any_captcha_during}")
    print("trusted_for_db=false  human_review_required=true  db_writes=false  (raw untrusted snapshot)")
    if load_error:
        print("NOTE: page load reported an error/block above. Reported as-is; no bypass attempted.")
    if len(captures) == 0:
        print("No pages captured (operator ended without capturing). No snapshot data saved beyond metadata.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
