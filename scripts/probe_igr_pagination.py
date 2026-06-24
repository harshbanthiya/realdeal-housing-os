#!/usr/bin/env python3
"""Pagination probe — opens browser, lets operator reach results page 1,
then walks through every page via postback, logging what's visible.
No captures, no DB writes. Ctrl-C to stop."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_igr_esearch_playwright import validate_url, ALLOWED_HOSTS

URL = "https://freesearchigrservice.maharashtra.gov.in/"
GRID = "RegistrationGrid"
PAGE_SEL = f"a[href*='__doPostBack'][href*='Page$']"
BTN_SEL  = "input[value='IndexII']"

def page_nums(pg):
    nums = []
    for lnk in pg.locator(PAGE_SEL).all():
        try:
            t = lnk.inner_text().strip()
            if t.isdigit(): nums.append(int(t))
        except Exception: pass
    return sorted(nums)

import re as _re

def dots(pg):
    return pg.locator(PAGE_SEL).filter(has_not_text=_re.compile(r'^\d+$'))

def click_wait(pg, locator, timeout=15000):
    try:
        locator.first.click()
        pg.wait_for_load_state("networkidle", timeout=timeout)
        return True
    except Exception as e:
        print(f"  [click ERROR] {e}")
        return False

def main():
    ok, msg = validate_url(URL)
    if not ok: print(msg); return

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx  = browser.new_context()
        page = ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        print("\nFill form → CAPTCHA → Search → wait for page-1 results.")
        input("Press Enter when page-1 results are visible: ")

        print(f"\n--- Probe: visible page links ---")
        nums = page_nums(page)
        btns = page.locator(BTN_SEL).count()
        print(f"  page_nums={nums}  IndexII_buttons={btns}")

        d = dots(page)
        print(f"\n--- Probe: dots links count={d.count()} ---")
        for i, lnk in enumerate(d.all()):
            try: print(f"  dot[{i}] text={lnk.inner_text().strip()!r}")
            except Exception as e: print(f"  dot[{i}] err={e}")

        print(f"\n--- Probe: click forward dot (last) ---")
        ok = click_wait(page, dots(page).last)
        nums2 = page_nums(page)
        print(f"  ok={ok}  page_nums={nums2}  dots_count={dots(page).count()}")

        print(f"\n--- Probe: click forward dot again (if any) ---")
        ok = click_wait(page, dots(page).last)
        nums3 = page_nums(page)
        print(f"  ok={ok}  page_nums={nums3}  dots_count={dots(page).count()}")

        print(f"\n--- Probe: walk all pages via DOM clicks ---")
        # go back to page 1 first
        for _ in range(5):
            lnk = page.locator(PAGE_SEL).filter(has_not_text=_re.compile(r'^1$'))
            p1 = page.locator(PAGE_SEL).filter(has_text=_re.compile(r'^1$'))
            if p1.count(): click_wait(page, p1); break
            click_wait(page, dots(page).first)
        for n in range(1, 30):
            nums = page_nums(page)
            btns = page.locator(BTN_SEL).count()
            print(f"  page {n}: visible_nums={nums}  buttons={btns}  dots={dots(page).count()}")
            nxt = page.locator(f"a[href*='Page${n+1}']")
            if nxt.count() == 0:
                d = dots(page)
                if d.count() == 0: print(f"  no next link and no dots — done at {n}"); break
                print(f"  clicking dot to reveal page {n+1}…")
                click_wait(page, d.last)
                nxt = page.locator(f"a[href*='Page${n+1}']")
                if nxt.count() == 0: print(f"  still no page {n+1} after dot — done"); break
            click_wait(page, nxt)

        input("\nDone probing. Press Enter to close browser: ")
        ctx.close(); browser.close()

if __name__ == "__main__":
    main()
