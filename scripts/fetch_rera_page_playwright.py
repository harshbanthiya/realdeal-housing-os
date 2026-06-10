#!/usr/bin/env python3
"""Phase 6.11 guarded MahaRERA single-page browser capture (Playwright) with gate handling.

Opens EXACTLY ONE user-supplied MahaRERA URL with Chromium and saves raw, UNTRUSTED
snapshots (screenshots / HTML / visible text / network summary / optional response bodies)
under the git-ignored exports/rera_snapshots/<timestamp>_<label>/ folder. It writes NOTHING
to the database, prints no page contents (and no CAPTCHA text), and does only a single
polite page load plus — at most — handling of two gates the operator has observed:

  1. An "external website" confirmation modal ("You are about to proceed to an external
     website. Click YES to proceed."). Detected always; YES is clicked ONLY if
     --accept-external-warning is supplied (and only for the single allowlisted URL).
  2. A CAPTCHA form on the public project view. Detected always; NEVER solved/read/OCR'd by
     the script and NEVER auto-submitted. Without --human-captcha-mode the script stops
     safely with status captcha_required. With --human-captcha-mode (headed) it pauses and
     lets a HUMAN manually solve the CAPTCHA in the visible browser, then captures.

Hard guards: URL host must be maharerait.maharashtra.gov.in or maharera.maharashtra.gov.in;
exactly one URL; no bulk scraping, no crawling, no looping over projects; no CAPTCHA/auth
bypass; no OCR; no solving services; no DB writes. metadata.json records trusted_for_db=false
and human_review_required=true. This script is the ONLY place in the project allowed to make
an external call, and only for one URL at a time.
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

# Polite bounds for optional response-body saving.
MAX_BODY_FILES = 25
MAX_BODY_BYTES = 512 * 1024

# Signals (lowercased substring matches) — used only to set booleans; never printed.
EXTERNAL_WARNING_SIGNALS = (
    "external website",
    "proceed to an external",
    "about to proceed",
    "click yes to proceed",
)
CAPTCHA_TEXT_SIGNALS = (
    "captcha",
    "enter the characters",
    "enter the text shown",
    "type the code",
    "i'm not a robot",
    "verify you are human",
)
CAPTCHA_SELECTORS = (
    "input[name*='captcha' i]",
    "input[id*='captcha' i]",
    "img[src*='captcha' i]",
    "img[id*='captcha' i]",
    "[class*='captcha' i]",
    "iframe[src*='recaptcha' i]",
    "iframe[src*='hcaptcha' i]",
)


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


def redact_url(url: str) -> str:
    """Drop any query string (could carry tokens/secrets); keep scheme+host+path only."""
    try:
        p = urlparse(url)
        path = (p.path or "")[:160]
        base = f"{p.scheme}://{p.hostname}{path}"
        if p.query:
            base += "?[redacted-query]"
        return base
    except Exception:  # noqa: BLE001
        return "[unparseable-url]"


def detect_external_warning(page) -> bool:
    """True if the external-site confirmation modal is present. Never prints page text."""
    try:
        body = (page.inner_text("body") or "").lower()
    except Exception:  # noqa: BLE001
        body = ""
    if any(sig in body for sig in EXTERNAL_WARNING_SIGNALS):
        return True
    return False


def detect_captcha(page) -> bool:
    """True if a CAPTCHA gate is present (text or DOM signal). Never reads/solves it."""
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


def click_external_yes(page, timeout_ms: int) -> bool:
    """Click the modal's YES button. Returns True on a successful click. One click only."""
    candidates = (
        "role=button[name=/^\\s*yes\\s*$/i]",
        "a:has-text('YES')",
        "button:has-text('YES')",
        "input[type='button'][value*='YES' i]",
        "input[type='submit'][value*='YES' i]",
    )
    for sel in candidates:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                loc.click(timeout=timeout_ms)
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Guarded single-URL MahaRERA Playwright capture (gates).")
    parser.add_argument("--url", default="", help="exactly one MahaRERA project URL")
    parser.add_argument("--output-label", required=True, help="short label for the snapshot folder")
    parser.add_argument("--timeout-ms", type=int, default=45000)

    headless = parser.add_mutually_exclusive_group()
    headless.add_argument("--headless", dest="headless", action="store_true", default=True)
    headless.add_argument("--headed", dest="headless", action="store_false")
    headless.add_argument("--headful", dest="headless", action="store_false",
                          help="alias for --headed (visible browser)")

    # Output toggles.
    parser.add_argument("--save-html", action="store_true")
    parser.add_argument("--save-screenshot", action="store_true")
    parser.add_argument("--save-visible-text", action="store_true")
    parser.add_argument("--save-network-summary", action="store_true")
    parser.add_argument("--save-response-bodies", action="store_true",
                        help="save same-host JSON/HTML response bodies (query strings redacted)")
    parser.add_argument("--response-body-url-filter", default="",
                        help="only save response bodies whose URL path contains this substring")

    # Gate handling.
    parser.add_argument("--accept-external-warning", action="store_true",
                        help="click YES on the external-site modal (allowlisted single URL only)")
    parser.add_argument("--human-captcha-mode", action="store_true",
                        help="headed; pause for a HUMAN to manually solve CAPTCHA (never auto-solved)")
    parser.add_argument("--pause-for-human", action="store_true",
                        help="block on Enter so the operator can act in the visible browser")
    parser.add_argument("--captcha-timeout-ms", type=int, default=180000,
                        help="max time to wait for the human / post-resume render signal")
    parser.add_argument("--wait-after-human-ms", type=int, default=2500)
    parser.add_argument("--wait-for-text", default="", help="optional text to wait for after load/resume")
    parser.add_argument("--wait-for-selector", default="", help="optional selector to wait for after load/resume")
    parser.add_argument("--post-load-wait-ms", type=int, default=3500,
                        help="settle time after initial load before gate detection")

    parser.add_argument("--apply", action="store_true",
                        help="actually open the browser and fetch (omit for a dry-run plan)")
    args = parser.parse_args()

    ok, host_or_msg = validate_url(args.url)
    if not ok:
        print(host_or_msg)
        return 1
    host = host_or_msg

    # --human-captcha-mode requires a visible browser so a human can act.
    if args.human_captcha_mode and args.headless:
        args.headless = False
        print("note: --human-captcha-mode forces a headed browser so a human can act.")

    # Default to the safest useful capture if nothing specific was requested.
    if not (args.save_html or args.save_screenshot or args.save_visible_text
            or args.save_network_summary or args.save_response_bodies):
        args.save_screenshot = True
        args.save_visible_text = True

    print(f"MahaRERA single-page capture. host={host}; label={args.output_label}; headless={args.headless}; "
          f"timeout_ms={args.timeout_ms}.")
    print("One URL only; no bulk scrape/crawl/loop; no CAPTCHA bypass/OCR/solver; no DB writes; "
          "snapshots are raw/untrusted.")
    print(f"gate flags: accept_external_warning={args.accept_external_warning}  "
          f"human_captcha_mode={args.human_captcha_mode}  pause_for_human={args.pause_for_human}")

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

    from datetime import datetime, timezone
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    folder_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = SNAPSHOT_ROOT / f"{folder_ts}_{safe_label(args.output_label)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Network bookkeeping — counts only; URLs are path-only with queries redacted.
    req_count = {"n": 0}
    responses: list[dict] = []
    failed_count = {"n": 0}
    saved_bodies: list[dict] = []  # {idx, ext}
    written: list[str] = []

    status_code = None
    load_error = None
    external_warning_detected = False
    external_warning_accepted_by_script = False
    captcha_detected = False
    captcha_solved_by_human = False
    final_status = "captured"

    def on_request(_req):
        req_count["n"] += 1

    def on_requestfailed(_req):
        failed_count["n"] += 1

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
        status = None
        try:
            status = r.status
        except Exception:  # noqa: BLE001
            pass
        rec = {"same_host": same_host, "json_like": json_like, "html_like": html_like,
               "status": status, "path": redact_url(r.url)}
        responses.append(rec)

        # Optional, bounded, redacted response-body capture.
        if (args.save_response_bodies and same_host and (json_like or html_like)
                and len(saved_bodies) < MAX_BODY_FILES):
            url_l = r.url.lower()
            if args.response_body_url_filter and args.response_body_url_filter.lower() not in url_l:
                return
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

    def wait_for_signals(timeout_ms: int) -> None:
        """Best-effort wait for an operator-supplied render signal. No looping/scraping."""
        if args.wait_for_selector:
            try:
                page.wait_for_selector(args.wait_for_selector, timeout=timeout_ms)
            except Exception:  # noqa: BLE001
                pass
        if args.wait_for_text:
            try:
                page.wait_for_function(
                    "t => document.body && document.body.innerText.includes(t)",
                    arg=args.wait_for_text, timeout=timeout_ms)
            except Exception:  # noqa: BLE001
                pass

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=args.headless)
            context = browser.new_context()
            page = context.new_page()
            page.on("request", on_request)
            page.on("requestfailed", on_requestfailed)
            page.on("response", on_response)

            try:
                resp = page.goto(args.url, timeout=args.timeout_ms, wait_until="domcontentloaded")
                status_code = resp.status if resp else None
                page.wait_for_timeout(max(0, args.post_load_wait_ms))
                wait_for_signals(min(args.timeout_ms, 15000))
            except Exception as exc:  # noqa: BLE001 - report load problems, don't work around
                load_error = type(exc).__name__

            # Snapshot before any gate handling (useful for review).
            if args.save_screenshot:
                try:
                    page.screenshot(path=str(out_dir / "screenshot_before_gate.png"), full_page=True)
                    written.append("screenshot_before_gate.png")
                except Exception:  # noqa: BLE001
                    pass

            # --- Gate 1: external-site confirmation modal ---
            external_warning_detected = detect_external_warning(page)
            if external_warning_detected:
                if args.accept_external_warning:
                    clicked = click_external_yes(page, timeout_ms=min(args.timeout_ms, 10000))
                    external_warning_accepted_by_script = clicked
                    if clicked:
                        page.wait_for_timeout(max(0, args.post_load_wait_ms))
                        wait_for_signals(min(args.timeout_ms, 15000))
                    else:
                        final_status = "external_warning_yes_not_found"
                else:
                    final_status = "external_warning_required"

            # --- Gate 2: CAPTCHA ---
            if final_status in ("captured",):
                captcha_detected = detect_captcha(page)
                if captcha_detected:
                    if not args.human_captcha_mode:
                        final_status = "captcha_required"
                    else:
                        # Human-in-the-loop: the operator solves the CAPTCHA in the visible
                        # browser and submits it THEMSELVES. The script never reads, OCRs,
                        # solves, or auto-submits it.
                        print("CAPTCHA detected. Headed human-in-the-loop mode:")
                        print("  -> In the OPEN browser window, manually solve the CAPTCHA and")
                        print("     submit it yourself so the project page renders.")
                        if args.pause_for_human:
                            try:
                                input("  -> Press Enter here AFTER the project page has rendered... ")
                            except EOFError:
                                print("  (no interactive stdin; falling back to wait-for-signal/timeout)")
                                page.wait_for_timeout(min(args.captcha_timeout_ms, 30000))
                        wait_for_signals(args.captcha_timeout_ms)
                        page.wait_for_timeout(max(0, args.wait_after_human_ms))
                        # Re-detect: if the gate is gone, the human cleared it.
                        captcha_solved_by_human = not detect_captcha(page)
                        final_status = "captured" if captcha_solved_by_human else "captcha_still_present"
                        if captcha_solved_by_human:
                            try:
                                page.screenshot(path=str(out_dir / "screenshot_after_human.png"),
                                                full_page=True)
                                written.append("screenshot_after_human.png")
                            except Exception:  # noqa: BLE001
                                pass

            # --- Capture remaining outputs (always save what we safely can) ---
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

    # Network summary — counts only, redacted candidate endpoint paths.
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
        "failed_responses": failed_resp + failed_count["n"],
        "candidate_endpoint_count": len(candidate_eps),
        "response_body_files_saved": len(saved_bodies),
        "candidate_endpoints": candidate_eps[:50],  # paths only; queries redacted
        "note": "counts only; no cookies/auth/headers/tokens stored; query strings redacted",
    }
    if args.save_network_summary:
        (out_dir / "network_summary.json").write_text(json.dumps(network_summary, indent=2), encoding="utf-8")
        written.append("network_summary.json")
    for b in saved_bodies:
        written.append(f"response_body_{b['idx']:03d}.{b['ext']}")

    metadata = {
        "url": args.url,
        "host": host,
        "fetched_at": fetched_at,
        "method": "playwright",
        "headless": args.headless,
        "http_status": status_code,
        "load_error": load_error,
        "status": final_status,
        "external_call_made": True,
        "trusted_for_db": False,
        "human_review_required": True,
        "external_warning_detected": external_warning_detected,
        "external_warning_accepted_by_script": external_warning_accepted_by_script,
        "captcha_detected": captcha_detected,
        "captcha_solved_by_human": captcha_solved_by_human,
        "db_writes": False,
        "files_written": written,
        "network_events_captured": total_responses,
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    written.append("metadata.json")

    # Print counts / booleans / PATHS only — never page contents or CAPTCHA text.
    print(f"snapshot folder: {out_dir}")
    print(f"files written ({len(written)}): {', '.join(written)}")
    print(f"http_status={status_code}  load_error={load_error}  status={final_status}")
    print(f"external_warning_detected={external_warning_detected}  "
          f"external_warning_accepted_by_script={external_warning_accepted_by_script}")
    print(f"captcha_detected={captcha_detected}  captcha_solved_by_human={captcha_solved_by_human}")
    print(f"network: requests={network_summary['total_requests']} responses={total_responses} "
          f"same_host={same_host} json_like={json_like} candidate_endpoints={len(candidate_eps)} "
          f"body_files={len(saved_bodies)}")
    print("trusted_for_db=false  human_review_required=true  db_writes=false  (raw untrusted snapshot)")
    if final_status == "external_warning_required":
        print("STOPPED SAFELY: external-site modal present and --accept-external-warning not supplied.")
    elif final_status == "captcha_required":
        print("STOPPED SAFELY: CAPTCHA present and --human-captcha-mode not supplied. No bypass attempted.")
    elif final_status == "captcha_still_present":
        print("CAPTCHA still present after the human window. Reported honestly; no bypass, no retry loop.")
    if load_error:
        print("NOTE: page load reported an error/block above. Reported as-is; no bypass attempted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
