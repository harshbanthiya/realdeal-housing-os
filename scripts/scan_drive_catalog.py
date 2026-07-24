#!/usr/bin/env python3
"""Scan the RDH 5TB drive into drive_files (migration 070) + emit docs/DRIVE-MAP.md.

The drive is the corpus. This walks it, classifies each file from its path and
name, and writes a catalog you can query — so the next session asks SQL instead
of running `find` across 45k files on a slow exFAT volume.

  --scan             walk the drive, upsert rows      (dry-run without --apply)
  --report           regenerate docs/DRIVE-MAP.md from what is catalogued
  --gaps             print the DB-vs-drive gap analysis

Inference is path-based on purpose: the folder tree already IS the taxonomy
here ("Excel Files/JUHU Brokers.csv" tells you everything). It is also fully
re-derivable, so re-scanning is always safe — no human decisions are stored.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db import run_psql, sql_literal as lit  # noqa: E402

DRIVE = Path("/Volumes/RDH 5TB")
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Areas worth cataloguing. The repo itself and the Postgres sparsebundle are
# excluded — they are code and database internals, not corpus.
AREAS = [
    "RDH DATA 2024/RDH ALL Footage",
    "RDH DATA 2024/RDH",
    "RDH DATA 2024/Non-RDH",
    "PT",
    "PJ",
    "PJ Iphone Backup",
    "Youtube Channel Downloaded ",
]

SKIP_DIR_PARTS = {
    "node_modules", ".git", "__pycache__", ".next", "venv", ".venv",
    "Library", "site-packages", ".cache",
}

# Building aliases → canonical building name. Ordered: first match wins, so put
# the specific before the generic.
BUILDING_ALIASES: list[tuple[str, str]] = [
    (r"imperial(\s*heights)?|(?<![a-z])ih(?![a-z])", "Imperial Heights"),
    (r"kalpataru|radiance", "Kalpataru Radiance"),
    (r"ekta\s*tripolis|tripolis|(?<![a-z])ekta(?![a-z])", "Ekta Tripolis"),
    (r"oberoi\s*esquire|esquire", "Oberoi Esquire"),
    (r"windsor\s*grande|windsor", "Windsor Grande Residences"),
    (r"dlf\s*(the\s*)?westpark|westpark|westend\s*heights", "DLF The Westpark"),
]

# doc_kind inference. Checked in order against the lowercased full path.
DOC_KINDS: list[tuple[str, str]] = [
    (r"brochure|e-?brochure|floor\s*plan|floorplan|layout", "brochure"),
    (r"index\s*ii|index2|igr|sro|7\s*12|search\s*result|maharera|rera", "igr_document"),
    (r"agreement|deed|noc|possession|allotment|lease|leave\s*(and|&)\s*licen", "agreement"),
    # Before broker_sheet: "1 Bhk inventory.xlsx" living in a "broker properties"
    # folder is a stock list, not a broker contact list.
    (r"inventory|stock\s*list|availability|half\s*save", "inventory"),
    (r"broker|dalal|channel\s*partner", "broker_sheet"),
    (r"tenant|rental|rent\s*roll|licensee", "tenant_sheet"),
    (r"owner|resident|member|society|flat\s*list|unit\s*list|mygate", "owner_sheet"),
    (r"invoice|brokerage|receipt|payment|bill", "financial"),
    (r"quotation|proposal|presentation|pitch|deck", "marketing"),
    (r"whatsapp|chat|contact|phonebook|vcard", "contact_export"),
]

CONTENT_CLASS: dict[str, str] = {
    **{e: "video" for e in ("mov", "mp4", "m4v", "avi", "mkv", "wmv", "mts", "mpg", "mpeg", "webm")},
    **{e: "image" for e in ("jpg", "jpeg", "png", "heic", "gif", "tiff", "tif", "cr2", "raw", "webp", "bmp")},
    **{e: "spreadsheet" for e in ("xlsx", "xls", "csv", "numbers", "tsv", "ods")},
    **{e: "document" for e in ("pdf", "doc", "docx", "txt", "rtf", "pages", "md", "odt")},
    **{e: "audio" for e in ("mp3", "m4a", "wav", "aac", "aiff", "caf")},
    **{e: "archive" for e in ("zip", "rar", "7z", "tar", "gz", "dmg")},
    **{e: "presentation" for e in ("ppt", "pptx", "key")},
}

# Extensions and names that are system/app/code noise, not corpus.
NOISE_EXT = {
    "plist", "abcdp", "aae", "db", "js", "ts", "c", "h", "o", "so", "dylib",
    "pyc", "map", "lock", "log", "cache", "bzz", "apkg", "ips", "sqlite",
    "sqlite3", "wal", "shm", "ini", "cfg", "bak", "tmp", "dat", "idx",
}
NOISE_NAME = re.compile(r"^(\._|\.ds_store|thumbs\.db|desktop\.ini|~\$)", re.I)


def _match(rules: list[tuple[str, str]], text: str) -> str | None:
    for pattern, value in rules:
        if re.search(pattern, text):
            return value
    return None


def classify(path: str, name: str, ext: str) -> dict:
    """Classify from the FILENAME first, falling back to the full path.

    A folder named "broker properties" would otherwise stamp every file inside
    it as a broker sheet — including "1 Bhk inventory.xlsx". Filename evidence
    is strong; folder evidence is a hint, and is recorded as lower confidence.
    """
    low_name, low_path = name.lower(), path.lower()

    building = _match(BUILDING_ALIASES, low_name)
    building_from_name = building is not None
    if building is None:
        building = _match(BUILDING_ALIASES, low_path)

    doc_kind = _match(DOC_KINDS, low_name)
    kind_from_name = doc_kind is not None
    if doc_kind is None:
        doc_kind = _match(DOC_KINDS, low_path)

    content_class = CONTENT_CLASS.get(ext, "other")
    is_noise = ext in NOISE_EXT or bool(NOISE_NAME.match(name)) or (content_class == "other" and not doc_kind)

    strong = sum([building_from_name, kind_from_name])
    confidence = "high" if strong == 2 else "medium" if strong == 1 else "low"

    return {"building_guess": building, "doc_kind": doc_kind,
            "content_class": content_class, "is_noise": is_noise,
            "confidence": confidence}


def walk() -> list[dict]:
    rows: list[dict] = []
    for area in AREAS:
        base = DRIVE / area
        if not base.exists():
            print(f"  [skip] missing: {area}", file=sys.stderr)
            continue
        count = 0
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_PARTS and not d.startswith(".")]
            for fn in filenames:
                if NOISE_NAME.match(fn):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
                if len(ext) > 8:
                    ext = ""
                rows.append({
                    "file_path": full,
                    "file_name": fn,
                    "parent_dir": dirpath,
                    "top_area": area,
                    "file_ext": ext,
                    "file_size_bytes": st.st_size,
                    "modified_at": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                    **classify(full, fn, ext),
                })
                count += 1
        print(f"  [{area}] {count} files", file=sys.stderr)
    return rows


def upsert(rows: list[dict], apply: bool) -> None:
    if not apply:
        print(f"DRY RUN — would upsert {len(rows)} rows (pass --apply to write)")
        return

    # Resolve building names → ids once. Two 'Imperial Heights' rows exist
    # (known duplicate anchor); MIN(id) keeps the mapping stable across scans.
    code, out = run_psql("SELECT name, min(id::text) FROM buildings GROUP BY name")
    if code != 0:
        sys.exit(f"error: {out}")
    ids = {line.split("|")[0]: line.split("|")[1] for line in out.splitlines() if "|" in line}

    # run_psql is a docker exec (~100ms); batch hard.
    BATCH = 500
    total = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        values = []
        for r in chunk:
            bid = ids.get(r["building_guess"] or "")
            values.append(
                "(" + ", ".join([
                    lit(r["file_path"]), lit(r["file_name"]), lit(r["parent_dir"]),
                    lit(r["top_area"]), lit(r["file_ext"]), str(int(r["file_size_bytes"])),
                    lit(r["modified_at"]) + "::timestamptz",
                    (lit(bid) + "::uuid") if bid else "NULL",
                    lit(r["building_guess"]) if r["building_guess"] else "NULL",
                    lit(r["doc_kind"]) if r["doc_kind"] else "NULL",
                    lit(r["content_class"]), lit(r["confidence"]),
                    "TRUE" if r["is_noise"] else "FALSE",
                ]) + ")"
            )
        sql = f"""
        INSERT INTO drive_files (file_path, file_name, parent_dir, top_area, file_ext,
          file_size_bytes, modified_at, building_id, building_guess, doc_kind,
          content_class, confidence, is_noise)
        VALUES {", ".join(values)}
        ON CONFLICT (file_path) DO UPDATE SET
          file_size_bytes = EXCLUDED.file_size_bytes,
          modified_at     = EXCLUDED.modified_at,
          building_id     = EXCLUDED.building_id,
          building_guess  = EXCLUDED.building_guess,
          doc_kind        = EXCLUDED.doc_kind,
          content_class   = EXCLUDED.content_class,
          confidence      = EXCLUDED.confidence,
          is_noise        = EXCLUDED.is_noise,
          last_seen_at    = now();
        """
        code, out = run_psql(sql)
        if code != 0:
            sys.exit(f"error at batch {i}: {out[:500]}")
        total += len(chunk)
        print(f"  upserted {total}/{len(rows)}", file=sys.stderr)
    print(f"status: ok\nrows: {total}")


def q(sql: str) -> list[list[str]]:
    code, out = run_psql(sql)
    if code != 0:
        sys.exit(f"error: {out}")
    return [line.split("|") for line in out.splitlines() if line]


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def report() -> None:
    totals = q("""SELECT count(*), count(*) FILTER (WHERE NOT is_noise),
                         pg_size_pretty(sum(file_size_bytes))
                  FROM drive_files""")[0]
    areas = q("""SELECT top_area, count(*) FILTER (WHERE NOT is_noise),
                        pg_size_pretty(sum(file_size_bytes) FILTER (WHERE NOT is_noise))
                 FROM drive_files GROUP BY 1 ORDER BY 2 DESC""")
    coverage = q("""SELECT building_name, files::text, brochures::text, owner_sheets::text,
                           broker_sheets::text, tenant_sheets::text, igr_docs::text,
                           videos::text, images::text, total_size
                    FROM vw_drive_building_coverage ORDER BY files DESC""")
    kinds = q("""SELECT coalesce(doc_kind,'(unclassified)'), content_class, count(*)::text,
                        pg_size_pretty(sum(file_size_bytes))
                 FROM drive_files WHERE NOT is_noise
                 GROUP BY 1,2 ORDER BY count(*) DESC LIMIT 25""")
    unattr = q("SELECT top_area, coalesce(doc_kind,'(none)'), content_class, files::text, size FROM vw_drive_unattributed LIMIT 20")
    biggest = q("""SELECT regexp_replace(parent_dir, '^/Volumes/RDH 5TB/', ''), count(*)::text,
                          pg_size_pretty(sum(file_size_bytes))
                   FROM drive_files WHERE NOT is_noise
                   GROUP BY 1 ORDER BY count(*) DESC LIMIT 25""")

    doc = f"""# DRIVE MAP — what is on the RDH 5TB drive and where

Generated by `scripts/scan_drive_catalog.py --report`. Do not hand-edit; re-run
the scanner instead. Catalogued in Postgres as `drive_files` (migration 070).

**{totals[1]} business files** catalogued ({totals[0]} scanned including noise),
{totals[2]} total.

## How to use this (read this first, next Claude)

The drive is the corpus. Do **not** `find` across it — it is a slow exFAT
volume with ~45k files. Query the catalog instead:

```sql
-- What do we have for a building?
SELECT * FROM vw_drive_building_coverage;

-- Every brochure for Kalpataru
SELECT file_path FROM drive_files
 WHERE building_guess = 'Kalpataru Radiance' AND doc_kind = 'brochure';

-- Any spreadsheet whose name mentions tenants
SELECT file_path, file_size_bytes FROM drive_files
 WHERE content_class = 'spreadsheet' AND file_name ILIKE '%tenant%' AND NOT is_noise;

-- Fuzzy filename search (pg_trgm index exists)
SELECT file_path FROM drive_files
 WHERE file_name % 'imperial owners' ORDER BY similarity(file_name, 'imperial owners') DESC LIMIT 20;
```

`building_guess`/`doc_kind` are **inferred from the path**, never human-verified.
`confidence` = high when the building name is in the filename itself, medium when
only in the folder path, low when unmatched. Treat medium/low as a hint, not fact.

## Areas

{md_table(["Area", "Business files", "Size"], areas)}

## Coverage per building

{md_table(["Building", "Files", "Brochures", "Owner sheets", "Broker sheets", "Tenant sheets", "IGR docs", "Videos", "Images", "Size"], coverage)}

## What kinds of things exist

{md_table(["doc_kind", "class", "Files", "Size"], kinds)}

## Business files we could not attribute to a building

These are the highest-value cleanup target: real documents and sheets whose
building is unknown, so no building workspace can surface them.

{md_table(["Area", "doc_kind", "class", "Files", "Size"], unattr)}

## Densest folders

{md_table(["Folder", "Files", "Size"], biggest)}

## When to upgrade this to real RAG

Today this is a **filename and path index**, which answers "where is X?" well
because the folder tree is already a taxonomy. It cannot answer "which
agreement mentions a lock-in clause?" or "what rent did we quote in 2019?".

Upgrade when a real question needs file *contents*, in this order — each step
is independently useful, so do not jump to embeddings:

1. **Extract text** from the ~2,400 PDFs and ~2,800 Word docs into a
   `drive_file_text` column/table (`pdftotext`, already a dependency for the
   IGR parsers). Postgres FTS over that answers most content questions.
2. **Whisper the videos** — `workers/video_transcriber.py` already exists;
   2,529 .mov + 1,019 .mp4 are entirely unsearchable today.
3. **Only then** embeddings, and only if FTS is measurably failing on
   paraphrase-style questions. pgvector on the same table.
"""
    out_path = PROJECT_ROOT / "docs" / "DRIVE-MAP.md"
    out_path.write_text(doc, encoding="utf-8")
    print(f"wrote {out_path} ({len(doc)} bytes)")


def gaps() -> None:
    print("=== Drive vs DB — per building ===")
    rows = q("""
      SELECT b.name,
             coalesce(d.files, 0)::text,
             (SELECT count(*) FROM building_units u WHERE u.building_id = b.id)::text,
             (SELECT count(*) FROM contact_property_relationships r WHERE r.building_id = b.id)::text,
             (SELECT count(*) FROM unit_registration_records x WHERE x.building_id = b.id)::text,
             (SELECT count(*) FROM media_assets m WHERE m.building_id = b.id)::text
        FROM buildings b
        LEFT JOIN (SELECT building_id, count(*) files FROM drive_files
                    WHERE NOT is_noise GROUP BY 1) d ON d.building_id = b.id
       ORDER BY 2::int DESC
    """)
    print(md_table(["Building", "Drive files", "Units", "Rels", "Registrations", "Media rows"], rows))

    print("\n=== Drive file kinds with NO corresponding DB ingest ===")
    print(md_table(["doc_kind", "Files", "Note"], q("""
      SELECT doc_kind, count(*)::text,
             CASE doc_kind
               WHEN 'broker_sheet'  THEN 'contacts table has 0 brokers — never ingested'
               WHEN 'tenant_sheet'  THEN 'tenancy comes only from IGR Index II, not these sheets'
               WHEN 'agreement'     THEN 'no agreement text is in the DB at all'
               WHEN 'financial'     THEN 'no financial data modelled'
               WHEN 'marketing'     THEN 'not linked to listing_content'
               ELSE 'see DRIVE-MAP.md'
             END
        FROM drive_files WHERE NOT is_noise AND doc_kind IS NOT NULL
       GROUP BY 1 ORDER BY count(*) DESC
    """)))


def selfcheck() -> None:
    """Classifier regressions, especially folder-vs-filename precedence."""
    def c(p):
        return classify(p, os.path.basename(p), p.rsplit(".", 1)[-1].lower())

    # The bug this precedence rule exists for: a "broker properties" folder must
    # not turn an inventory spreadsheet into a broker sheet.
    r = c("/x/1 Daily Work Sheet/New folder/broker properties/1 Bhk inventory.xlsx")
    assert r["doc_kind"] == "inventory", r

    r = c("/x/Excel Files/JUHU Brokers.csv")
    assert r["doc_kind"] == "broker_sheet" and r["content_class"] == "spreadsheet", r

    r = c("/x/Ekta Tripolis/tripolis_brochure.pdf")
    assert r["building_guess"] == "Ekta Tripolis" and r["doc_kind"] == "brochure", r
    assert r["confidence"] == "high", r

    # Building only in the folder → medium, not high.
    r = c("/x/Kalpataru Radiance/misc/scan001.pdf")
    assert r["building_guess"] == "Kalpataru Radiance" and r["confidence"] in ("medium", "low"), r

    r = c("/x/Imperial brochure.pdf")
    assert r["building_guess"] == "Imperial Heights", r

    # Noise stays noise.
    assert c("/x/Library/prefs/com.apple.thing.plist")["is_noise"] is True
    assert c("/x/RDH ALL Footage/IH A 2105 YT Final HQ.mov")["content_class"] == "video"

    print("selfcheck: ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--gaps", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:
        selfcheck()
        return
    if a.scan:
        print("scanning…", file=sys.stderr)
        upsert(walk(), a.apply)
    if a.report:
        report()
    if a.gaps:
        gaps()
    if not (a.scan or a.report or a.gaps or a.selfcheck):
        ap.print_help()


if __name__ == "__main__":
    main()
