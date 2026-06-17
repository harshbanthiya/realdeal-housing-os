#!/usr/bin/env python3
"""Human-in-the-loop IGR document-number search -> IndexII capture.

This script automates the repetitive, non-CAPTCHA parts of the IGR "Document
Number" search workflow:

  1. Fill registration type, district, SRO, year, and document number.
  2. Pause while the operator enters CAPTCHA in the browser.
  3. Click Search after operator confirmation.
  4. Click the matching IndexII link.
  5. Save the opened IndexII tab as HTML, text, screenshot, and best-effort PDF.
  6. Verify the saved report contains the expected document number.
  7. Continue to the next queue row.

It never reads, OCRs, solves, bypasses, or submits CAPTCHA without the operator's
confirmation. It writes no DB rows. Outputs stay under exports/ and may contain
public-register PII.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUEUE_CSV = PROJECT_ROOT / "exports" / "igr_kalpataru_timelines" / "kalpataru_doc_search_queue.csv"
OUTPUT_ROOT = PROJECT_ROOT / "exports" / "igr_doc_search_index2"
DEFAULT_URL = "https://freesearchigrservice.maharashtra.gov.in/"
ALLOWED_HOSTS = {"freesearchigrservice.maharashtra.gov.in"}
DISTRICT_MATCHES = ("मुंबई उपनगर", "Mumbai Suburban")


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")[:120] or "item"


def now_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
        raise SystemExit(f"Refusing URL outside allowed IGR host: {url}")


def load_queue(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return rows


def wanted_rows(rows: list[dict[str, str]], args: argparse.Namespace) -> list[dict[str, str]]:
    out = rows
    if args.only_missing:
        out = [r for r in out if str(r.get("has_index22_pdf", "")).lower() not in ("true", "1", "yes")]
    if args.category:
        cats = {c.strip().lower() for c in args.category.split(",") if c.strip()}
        out = [r for r in out if r.get("category", "").lower() in cats]
    if args.sro:
        needle = args.sro.lower()
        out = [r for r in out if needle in r.get("sro_office", "").lower() or needle in r.get("sro_code", "").lower()]
    if args.start_at_doc:
        docs = [r.get("doc_number") for r in out]
        if args.start_at_doc in docs:
            out = out[docs.index(args.start_at_doc):]
    if args.limit:
        out = out[: args.limit]
    return out


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def option_select_js() -> str:
    return r"""
({kind, labels}) => {
  const clean = (v) => String(v || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const wanted = labels.map(clean).filter(Boolean);
  const selects = Array.from(document.querySelectorAll('select'));
  for (const sel of selects) {
    const options = Array.from(sel.options || []);
    const hit = options.find((opt) => {
      const text = clean(opt.textContent || opt.label || opt.value);
      const value = clean(opt.value);
      return wanted.some((w) => text.includes(w) || value.includes(w));
    });
    if (hit) {
      sel.value = hit.value;
      sel.dispatchEvent(new Event('change', { bubbles: true }));
      return { ok: true, kind, value: hit.value, text: hit.textContent || hit.label || hit.value };
    }
  }
  return { ok: false, kind, labels, selectCount: selects.length };
}
"""


def click_registration_type(page, row: dict[str, str], override: str = "") -> str:
    choices = [
        override,
        row.get("registration_type_primary") or "",
        row.get("registration_type_fallback") or "",
        "eRegistration",
        "Regular",
        "iSarita 2.0",
    ]
    seen = set()
    for label in choices:
        if not label:
            continue
        if label in seen:
            continue
        seen.add(label)
        try:
            page.get_by_text(label, exact=True).click(timeout=1500)
            return label
        except Exception:  # noqa: BLE001
            pass
        try:
            page.locator(f"label:has-text('{label}')").click(timeout=1500)
            return label
        except Exception:  # noqa: BLE001
            pass
    # Last resort: click Regular-ish radio by nearby text.
    try:
        page.get_by_text("Regular").click(timeout=1500)
        return "Regular"
    except Exception:  # noqa: BLE001
        return ""


def select_dropdown(page, kind: str, labels: list[str]) -> dict:
    return page.evaluate(option_select_js(), {"kind": kind, "labels": labels})


def fill_doc_number(page, doc_number: str) -> bool:
    # Avoid CAPTCHA textbox: prefer inputs that are not placeholder/name/id captcha.
    result = page.evaluate(
        r"""
        (docNo) => {
          const inputs = Array.from(document.querySelectorAll('input'));
          const visible = (el) => {
            const st = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return st.visibility !== 'hidden' && st.display !== 'none' && r.width > 0 && r.height > 0;
          };
          const textInputs = inputs.filter((el) => {
            const t = (el.type || 'text').toLowerCase();
            const hay = `${el.id || ''} ${el.name || ''} ${el.placeholder || ''}`.toLowerCase();
            return visible(el) && ['text', 'search', 'tel', 'number', ''].includes(t) && !hay.includes('captcha');
          });
          let target = textInputs.find((el) => `${el.id || ''} ${el.name || ''}`.toLowerCase().includes('doc'));
          if (!target) target = textInputs[0];
          if (!target) return false;
          target.focus();
          target.value = docNo;
          target.dispatchEvent(new Event('input', { bubbles: true }));
          target.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        }
        """,
        str(doc_number),
    )
    return bool(result)


def click_search(page) -> None:
    for text in ("Search", "शोध"):
        try:
            page.get_by_text(text, exact=False).click(timeout=2000)
            return
        except Exception:  # noqa: BLE001
            pass
    page.evaluate(
        r"""
        () => {
          const buttons = Array.from(document.querySelectorAll('button,input[type=submit],input[type=button],a'));
          const b = buttons.find((el) => /search|शोध/i.test(el.textContent || el.value || ''));
          if (!b) throw new Error('Search button not found');
          b.click();
        }
        """
    )


def page_has_captcha_error(page) -> bool:
    try:
        body = page.inner_text("body", timeout=3000).lower()
    except Exception:  # noqa: BLE001
        return False
    return "captcha is incorrect" in body or "captcha" in body and "incorrect" in body


def find_index2_locator(page, doc_number: str):
    # Prefer the row containing the target doc number.
    rows = page.locator("tr").filter(has_text=str(doc_number))
    try:
        if rows.count():
            row = rows.first
            for pattern in ("IndexII", "Index II", "सूची"):
                loc = row.get_by_text(pattern, exact=False)
                if loc.count():
                    return loc.first
            links = row.locator("a,button,input[type=button]")
            if links.count():
                return links.last
    except Exception:  # noqa: BLE001
        pass
    for pattern in ("IndexII", "Index II", "सूची"):
        loc = page.get_by_text(pattern, exact=False)
        try:
            if loc.count():
                return loc.first
        except Exception:  # noqa: BLE001
            pass
    return None


def report_contains_doc(text: str, doc_number: str, year: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    return f"{doc_number}/{year}" in compact or f"दस्तक्रमांक:{doc_number}/{year}" in compact or doc_number in compact


def save_index2_page(detail_page, out_dir: Path, row: dict[str, str]) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = row["doc_number"]
    year = row["registration_year"]
    prefix = safe_filename(f"{row.get('apartment_key','unit')}_doc-{doc}_{year}")
    result = {"doc_number": doc, "year": year, "files": {}, "verified_doc_number": False, "errors": []}

    try:
        detail_page.wait_for_load_state("domcontentloaded", timeout=30000)
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"domcontentloaded:{type(exc).__name__}")
    try:
        detail_page.wait_for_timeout(1000)
    except Exception:  # noqa: BLE001
        pass

    try:
        html_text = detail_page.content()
        html_path = out_dir / f"{prefix}.html"
        html_path.write_text(html_text, encoding="utf-8")
        result["files"]["html"] = str(html_path)
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"html:{type(exc).__name__}")

    text = ""
    try:
        text = detail_page.inner_text("body", timeout=10000)
        text_path = out_dir / f"{prefix}.txt"
        text_path.write_text(text, encoding="utf-8")
        result["files"]["text"] = str(text_path)
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"text:{type(exc).__name__}")

    try:
        png_path = out_dir / f"{prefix}.png"
        detail_page.screenshot(path=str(png_path), full_page=True)
        result["files"]["screenshot"] = str(png_path)
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"screenshot:{type(exc).__name__}")

    # Best-effort print-to-PDF via Chrome DevTools. This is the closest automated
    # equivalent to "Save as PDF" for the opened IndexII report.
    try:
        session = detail_page.context.new_cdp_session(detail_page)
        pdf = session.send("Page.printToPDF", {"printBackground": True, "preferCSSPageSize": True})
        pdf_path = out_dir / f"{prefix}.pdf"
        pdf_path.write_bytes(base64.b64decode(pdf["data"]))
        result["files"]["pdf"] = str(pdf_path)
    except Exception as exc:  # noqa: BLE001
        result["errors"].append(f"pdf:{type(exc).__name__}")

    result["verified_doc_number"] = report_contains_doc(text, doc, year)
    return result


def write_progress(progress_path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "timestamp", "status", "doc_number", "registration_year", "apartment_key", "category",
        "sro_office", "message", "output_dir", "verified_doc_number",
    ]
    exists = progress_path.exists()
    with progress_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description="Human-in-loop IGR Doc Search -> IndexII fetcher.")
    parser.add_argument("--queue", type=Path, default=QUEUE_CSV)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output-label", default="kalpataru_doc_search")
    parser.add_argument("--only-missing", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--category", default="", help="comma-separated categories, e.g. tenancy")
    parser.add_argument("--sro", default="", help="filter queue by SRO text/code")
    parser.add_argument("--start-at-doc", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=45000)
    parser.add_argument(
        "--registration-type",
        default="eRegistration",
        help="preferred radio option from the screenshot; falls back to queue hints if unavailable",
    )
    parser.add_argument("--apply", action="store_true", help="open headed browser and perform operator-driven fetch")
    args = parser.parse_args()

    validate_url(args.url)
    rows = wanted_rows(load_queue(args.queue), args)
    print(f"IGR doc-search IndexII fetcher. Queue rows selected: {len(rows)}")
    print("Human operator must enter CAPTCHA for each search. No CAPTCHA OCR/solver/bypass is used.")
    for row in rows[:20]:
        print(
            f"  {row['apartment_key']:>6} {row['category']:<11} doc={row['doc_number']} "
            f"year={row['registration_year']} sro={row['sro_office']}"
        )
    if len(rows) > 20:
        print(f"  ... {len(rows) - 20} more")
    if not args.apply:
        print("Dry run only. Re-run with --apply to open the browser.")
        return 0

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("Playwright not installed in this Python environment.")
        print("Try: python3 -m pip install playwright && python3 -m playwright install chromium")
        return 2

    out_dir = OUTPUT_ROOT / f"{now_label()}_{safe_filename(args.output_label)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    progress_path = out_dir / "progress.csv"
    manifest: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(args.url, timeout=args.timeout_ms, wait_until="domcontentloaded")

        for index, row in enumerate(rows, 1):
            print("\n" + "=" * 90)
            print(f"[{index}/{len(rows)}] {row['apartment_key']} {row['category']} doc={row['doc_number']} year={row['registration_year']} sro={row['sro_office']}")

            while True:
                try:
                    reg_type = click_registration_type(page, row, args.registration_type)
                    district = select_dropdown(page, "district", list(DISTRICT_MATCHES))
                    sro = select_dropdown(page, "sro", [row.get("sro_office", ""), row.get("sro_code", "")])
                    year = select_dropdown(page, "year", [row.get("registration_year", "")])
                    filled_doc = fill_doc_number(page, row["doc_number"])
                    print(
                        f"Filled: reg_type={reg_type} district={district.get('text')} "
                        f"sro={sro.get('text')} year={year.get('text')} doc_field={filled_doc}"
                    )
                except Exception as exc:  # noqa: BLE001
                    msg = f"fill_failed:{type(exc).__name__}:{exc}"
                    print(msg)
                    write_progress(progress_path, [{**row, "timestamp": now_label(), "status": "fill_failed", "message": msg}])
                    break

                print("Solve CAPTCHA in the browser. Then press Enter here to click Search.")
                cmd = input("Enter=search, s=skip, q=quit: ").strip().lower()
                if cmd == "q":
                    save_json(out_dir / "manifest.json", manifest)
                    return 0
                if cmd == "s":
                    write_progress(progress_path, [{**row, "timestamp": now_label(), "status": "skipped", "message": "operator skipped"}])
                    break

                try:
                    click_search(page)
                    page.wait_for_load_state("networkidle", timeout=args.timeout_ms)
                except PlaywrightTimeoutError:
                    pass
                except Exception as exc:  # noqa: BLE001
                    print(f"search click/load warning: {type(exc).__name__}: {exc}")

                if page_has_captcha_error(page):
                    print("CAPTCHA was rejected by site. Re-enter CAPTCHA in browser and try this same doc again.")
                    continue

                loc = find_index2_locator(page, row["doc_number"])
                if loc is None:
                    msg = "IndexII link not found for result row."
                    print(msg)
                    write_progress(progress_path, [{**row, "timestamp": now_label(), "status": "no_indexii_link", "message": msg}])
                    break

                detail_dir = out_dir / safe_filename(f"{index:03d}_{row['apartment_key']}_doc-{row['doc_number']}")
                try:
                    with context.expect_page(timeout=args.timeout_ms) as popup_info:
                        loc.click()
                    detail_page = popup_info.value
                    saved = save_index2_page(detail_page, detail_dir, row)
                    try:
                        detail_page.close()
                    except Exception:  # noqa: BLE001
                        pass
                except PlaywrightTimeoutError:
                    # Some versions may open in same tab instead of popup.
                    print("No popup detected; trying to save current page.")
                    saved = save_index2_page(page, detail_dir, row)
                except Exception as exc:  # noqa: BLE001
                    msg = f"indexii_click_failed:{type(exc).__name__}:{exc}"
                    print(msg)
                    write_progress(progress_path, [{**row, "timestamp": now_label(), "status": "indexii_click_failed", "message": msg}])
                    break

                status = "verified" if saved.get("verified_doc_number") else "saved_unverified"
                print(f"Saved IndexII: {status} -> {detail_dir}")
                manifest.append({**row, "saved": saved})
                write_progress(
                    progress_path,
                    [
                        {
                            **row,
                            "timestamp": now_label(),
                            "status": status,
                            "message": "; ".join(saved.get("errors", [])),
                            "output_dir": str(detail_dir),
                            "verified_doc_number": saved.get("verified_doc_number"),
                        }
                    ],
                )
                # Return to the search form/results page for the next doc. The form normally
                # remains filled except CAPTCHA, so we refill every loop anyway.
                break

        save_json(out_dir / "manifest.json", manifest)
        print(f"\nDone. Output folder: {out_dir}")
        print(f"Progress CSV: {progress_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
