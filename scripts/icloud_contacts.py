#!/usr/bin/env python3
"""iCloud CardDAV client — update the sales phone's contacts IN PLACE.

Her exported .vcf files carry no UID (Apple strips it), so they can only ever be
read. Re-importing an enriched .vcf would create a second copy of every contact
and double the mess. CardDAV is the only safe write path: pull the live cards
with their href/etag, modify, PUT back with If-Match.

  --verify                 log in, discover the address book, count cards
  --pull   [--apply]       mirror the live cards into icloud_cards (migration 074)
  --push   [--apply] [--limit N]
                           apply APPROVED to_phone proposals, in place
  --rollback [--apply]     restore original_vcard for everything we wrote

Credentials (never committed) in secrets/icloud.env:
    ICLOUD_USER=her-apple-id@example.com
    ICLOUD_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx     # appleid.apple.com → App-Specific

Stdlib only (urllib + ElementTree); no new dependency for one HTTP dialect.

SAFETY: dry-run everywhere by default. --push refuses to run without --apply,
writes at most --limit cards per run (default 25), stops on the first error,
and always stores the pre-write body so --rollback can undo it.
"""
from __future__ import annotations

import argparse
import base64
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db import run_psql, sql_literal as lit  # noqa: E402

SECRETS = Path(__file__).resolve().parents[1] / "secrets" / "icloud.env"
ROOT_URL = "https://contacts.icloud.com"
DAV = "{DAV:}"
CARD = "{urn:ietf:params:xml:ns:carddav}"
UA = "RealDealHousingOS/1.0"


def creds() -> tuple[str, str]:
    if not SECRETS.exists():
        sys.exit(f"missing {SECRETS} — see this script's docstring for the format.")
    vals = {}
    for line in SECRETS.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()
    user, pw = vals.get("ICLOUD_USER"), vals.get("ICLOUD_APP_PASSWORD")
    if not user or not pw:
        sys.exit("ICLOUD_USER / ICLOUD_APP_PASSWORD not set in secrets/icloud.env")
    return user, pw


def dav(method: str, url: str, body: str = "", depth: str = "0",
        extra: dict | None = None) -> tuple[int, str]:
    user, pw = creds()
    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "User-Agent": UA,
        "Depth": depth,
        "Content-Type": "text/xml; charset=utf-8",
    }
    if extra:
        headers.update(extra)
    req = urllib.request.Request(url, data=body.encode() if body else None,
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        return 0, str(e)


def absolute(href: str) -> str:
    return href if href.startswith("http") else ROOT_URL + href


def discover() -> str:
    """Root → principal → address-book home → the contacts collection."""
    code, xml = dav("PROPFIND", ROOT_URL + "/",
                    '<d:propfind xmlns:d="DAV:"><d:prop>'
                    "<d:current-user-principal/></d:prop></d:propfind>")
    if code not in (207, 200):
        sys.exit(f"login/discovery failed (HTTP {code}). Check the app-specific "
                 f"password.\n{xml[:300]}")
    principal = next((e.text for e in ET.fromstring(xml).iter(DAV + "href")
                      if e.text and "principal" in e.text), None)
    if not principal:
        sys.exit("could not find current-user-principal")

    code, xml = dav("PROPFIND", absolute(principal),
                    '<d:propfind xmlns:d="DAV:" '
                    'xmlns:c="urn:ietf:params:xml:ns:carddav"><d:prop>'
                    "<c:addressbook-home-set/></d:prop></d:propfind>")
    home = next((e.text for e in ET.fromstring(xml).iter(DAV + "href")
                 if e.text and "principal" not in e.text), None)
    if not home:
        sys.exit("could not find addressbook-home-set")

    code, xml = dav("PROPFIND", absolute(home),
                    '<d:propfind xmlns:d="DAV:"><d:prop>'
                    "<d:resourcetype/><d:displayname/></d:prop></d:propfind>",
                    depth="1")
    for resp in ET.fromstring(xml).iter(DAV + "response"):
        rtype = resp.find(f".//{DAV}resourcetype")
        if rtype is not None and rtype.find(CARD + "addressbook") is not None:
            href = resp.find(DAV + "href")
            if href is not None and href.text:
                return absolute(href.text)
    sys.exit("no addressbook collection found")


def norm_phone(raw: object) -> str | None:
    d = re.sub(r"\D", "", str(raw or "")).lstrip("0")
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    elif len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return "+91" + d if len(d) == 10 and d[0] in "6789" else None


def card_fields(vcard: str) -> tuple[str, str | None, str | None]:
    """(display_name, first mobile, uid) out of a vCard body."""
    fn, phone, uid = "", None, None
    for line in vcard.splitlines():
        line = line.strip()
        if line.upper().startswith("FN") and ":" in line:
            fn = line.split(":", 1)[1].strip()
        elif line.upper().startswith("UID") and ":" in line:
            uid = line.split(":", 1)[1].strip()
        elif line.upper().startswith("TEL") and ":" in line and phone is None:
            phone = norm_phone(line.split(":", 1)[1])
    return fn, phone, uid


def q(sql: str) -> list[list[str]]:
    code, out = run_psql(sql)
    if code != 0:
        sys.exit(f"db error: {out[:400]}")
    return [ln.split("|") for ln in out.splitlines() if ln]


def pull(apply: bool) -> None:
    book = discover()
    print(f"address book: {book}")
    code, xml = dav("PROPFIND", book,
                    '<d:propfind xmlns:d="DAV:"><d:prop>'
                    "<d:getetag/><d:resourcetype/></d:prop></d:propfind>", depth="1")
    if code not in (207, 200):
        sys.exit(f"listing failed (HTTP {code})")

    entries = []
    for resp in ET.fromstring(xml).iter(DAV + "response"):
        href = resp.find(DAV + "href")
        etag = resp.find(f".//{DAV}getetag")
        if href is not None and href.text and href.text.endswith(".vcf"):
            entries.append((href.text, (etag.text or "").strip('"') if etag is not None else ""))
    print(f"cards on server: {len(entries)}")
    if not apply:
        print("DRY RUN — pass --apply to mirror them into icloud_cards.")
        return

    written = 0
    for i in range(0, len(entries), 100):
        values = []
        for href, etag in entries[i:i + 100]:
            code, body = dav("GET", absolute(href), extra={"Content-Type": "text/vcard"})
            if code != 200:
                continue
            fn, phone, uid = card_fields(body)
            values.append("(" + ", ".join([
                lit(href), lit(uid) if uid else "NULL", lit(etag),
                lit(fn[:200]), lit(phone) if phone else "NULL", lit(body),
            ]) + ")")
        if values:
            q(f"""INSERT INTO icloud_cards (href, uid, etag, display_name, phone, raw_vcard)
                  VALUES {", ".join(values)}
                  ON CONFLICT (href) DO UPDATE SET
                    etag = EXCLUDED.etag, display_name = EXCLUDED.display_name,
                    phone = EXCLUDED.phone, raw_vcard = EXCLUDED.raw_vcard,
                    pulled_at = now()""")
            written += len(values)
        print(f"  pulled {written}/{len(entries)}", file=sys.stderr)
    print(f"status: ok\ncards: {written}")


def rewrite_vcard(body: str, new_name: str, note: str) -> str:
    """Replace FN/N and set our NOTE, leaving every other property intact."""
    out, seen_note = [], False
    for line in body.splitlines():
        u = line.upper()
        if u.startswith("FN") and ":" in line:
            out.append(f"FN:{new_name}")
        elif u.startswith("N:") or (u.startswith("N;") and ":" in line):
            out.append(f"N:{new_name};;;;")
        elif u.startswith("NOTE") and ":" in line:
            out.append(f"NOTE:{note}")
            seen_note = True
        elif u.startswith("END:VCARD"):
            if not seen_note:
                out.append(f"NOTE:{note}")
            out.append(line)
        else:
            out.append(line)
    return "\r\n".join(out) + "\r\n"


def push(apply: bool, limit: int) -> None:
    rows = q(f"""
        SELECT p.id::text, c.href, c.etag, c.raw_vcard, p.proposed_value,
               coalesce(p.note_block,''), c.display_name
          FROM phonebook_proposals p
          JOIN icloud_cards c ON c.phone = p.phone
         WHERE p.direction = 'to_phone' AND p.status = 'approved'
           AND p.applied_at IS NULL
           AND c.write_error IS NULL
         ORDER BY p.reviewed_at
         LIMIT {int(limit)}""")
    print(f"approved and ready to write: {len(rows)}")
    if not rows:
        print("nothing to do (approve some phonebook_rename cohorts first)")
        return
    for r in rows[:5]:
        print(f"  {r[6][:40]:<40} → {r[4][:40]}")
    if not apply:
        print(f"DRY RUN — would write {len(rows)} cards. Pass --apply.")
        return

    ok = 0
    for pid, href, etag, raw, newname, note, _old in rows:
        body = rewrite_vcard(raw, newname, note.replace("\\n", "\n"))
        code, resp = dav("PUT", absolute(href), body,
                         extra={"Content-Type": "text/vcard; charset=utf-8",
                                "If-Match": f'"{etag}"'})
        if code in (200, 201, 204):
            q(f"""UPDATE icloud_cards
                     SET original_vcard = coalesce(original_vcard, {lit(raw)}),
                         written_at = now(), raw_vcard = {lit(body)}
                   WHERE href = {lit(href)}""")
            q(f"UPDATE phonebook_proposals SET status='applied', applied_at=now() "
              f"WHERE id={lit(pid)}::uuid")
            ok += 1
        else:
            q(f"UPDATE icloud_cards SET write_error={lit(f'HTTP {code}: {resp[:200]}')} "
              f"WHERE href={lit(href)}")
            print(f"STOPPED on error (HTTP {code}) after {ok} writes: {resp[:200]}")
            break
    print(f"status: ok\nwritten: {ok}")


def rollback(apply: bool) -> None:
    rows = q("""SELECT href, original_vcard, etag FROM icloud_cards
                 WHERE written_at IS NOT NULL AND original_vcard IS NOT NULL""")
    print(f"cards to restore: {len(rows)}")
    if not apply:
        print("DRY RUN — pass --apply to restore.")
        return
    ok = 0
    for href, original, etag in rows:
        code, _ = dav("PUT", absolute(href), original,
                      extra={"Content-Type": "text/vcard; charset=utf-8"})
        if code in (200, 201, 204):
            q(f"""UPDATE icloud_cards SET raw_vcard = original_vcard,
                     written_at = NULL, original_vcard = NULL WHERE href = {lit(href)}""")
            ok += 1
    print(f"restored: {ok}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=25)
    a = ap.parse_args()

    if a.verify:
        book = discover()
        code, xml = dav("PROPFIND", book,
                        '<d:propfind xmlns:d="DAV:"><d:prop><d:getetag/>'
                        "</d:prop></d:propfind>", depth="1")
        n = len([h for h in ET.fromstring(xml).iter(DAV + "href")
                 if h.text and h.text.endswith(".vcf")])
        print(f"connected. address book: {book}\ncards visible: {n}")
    elif a.pull:
        pull(a.apply)
    elif a.push:
        push(a.apply, a.limit)
    elif a.rollback:
        rollback(a.apply)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
