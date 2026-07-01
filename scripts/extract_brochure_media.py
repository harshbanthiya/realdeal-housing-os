#!/usr/bin/env python3
"""
MIS Phase C — Brochure page extractor.

Renders each mapped page of the DLF Westpark brochure as a high-res PNG,
saves under exports/media/dlf-westpark/ (git-ignored), and inserts rows
into media_assets with correct building_id, configuration_type, asset_type,
asset_level.

Usage:
  python scripts/extract_brochure_media.py           # dry-run
  python scripts/extract_brochure_media.py --apply   # write files + DB rows
  python scripts/extract_brochure_media.py --revert  # delete inserted rows (files stay)
  python scripts/extract_brochure_media.py --page 11 # dry-run single page
"""

import sys
import argparse
import hashlib
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    print("ERROR: pymupdf not installed. Run: pip install pymupdf", file=sys.stderr)
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed.", file=sys.stderr)
    sys.exit(1)

# ── config ────────────────────────────────────────────────────────────────────

BROCHURE_PATH = Path("/Volumes/RDH 5TB/RDH DATA 2024/RDH ALL Footage/ALL PROJECTS/DLF Westpark/Presenter 1.pdf")
OUTPUT_DIR = Path(__file__).parent.parent / "exports" / "media" / "dlf-westpark"
DLF_BUILDING_ID = "a642e2db-27e6-4aba-b4ec-056c3f3edf01"
RENDER_SCALE = 2.0  # 2x = ~144dpi from 72dpi source

# ── page map (1-indexed, mirrors brochure page numbers) ───────────────────────
# Each entry: asset_level, asset_type, title (optional), tower (for tower level),
#             configs (list of config_type strings, for configuration level)

PAGE_MAP = {
    # ── building level ─────────────────────────────────────────────────────
    1:  {"asset_level": "building", "asset_type": "exterior",     "title": "Cover exterior"},
    2:  {"asset_level": "building", "asset_type": "exterior",     "title": "Building exterior all towers"},
    3:  {"asset_level": "building", "asset_type": "amenity",      "title": "Pool and landscape overview"},
    4:  {"asset_level": "building", "asset_type": "location_map", "title": "Connectivity map"},
    5:  {"asset_level": "building", "asset_type": "master_layout","title": "Master layout plan"},

    # ── Tower 02 overall floor plans ──────────────────────────────────────
    6:  {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T02", "title": "T02 typical floor plan"},
    7:  {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T02", "title": "T02 refuge floor plan 7 15 22 29"},
    8:  {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T02", "title": "T02 refuge floor plan 36"},
    9:  {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T02", "title": "T02 duplex floor plan 39 lower"},
    10: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T02", "title": "T02 duplex floor plan 40 upper"},

    # ── Tower 02 unit plans ───────────────────────────────────────────────
    11: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T02-3BHK-01", "T02-3BHK-02"]},
    12: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T02-4BHK-01"]},
    13: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T02-5BHK-01"]},
    14: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T02-4BHK-DUPLEX-01"]},

    # ── Tower 03 overall floor plans ──────────────────────────────────────
    15: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T03", "title": "T03 typical floor plan"},
    16: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T03", "title": "T03 refuge floor plan 7 15 22 29"},
    17: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T03", "title": "T03 refuge floor plan 36"},
    18: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T03", "title": "T03 duplex floor plan 39 lower"},
    19: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T03", "title": "T03 duplex floor plan 40 upper"},

    # ── Tower 03 unit plans ───────────────────────────────────────────────
    20: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T03-3BHK-01", "T03-3BHK-02"]},
    21: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T03-3BHK-03", "T03-3BHK-04"]},
    22: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T03-4BHK-03"]},
    23: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T03-4BHK-DUPLEX-01"]},
    24: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T03-4BHK-DUPLEX-02"]},

    # ── Tower 04 overall floor plans ──────────────────────────────────────
    25: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T04", "title": "T04 typical floor plan"},
    26: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T04", "title": "T04 refuge floor plan 7 15 22 29"},
    27: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T04", "title": "T04 refuge floor plan 36"},
    28: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T04", "title": "T04 duplex floor plan 39 lower"},
    29: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T04", "title": "T04 duplex floor plan 40 upper"},

    # ── Tower 04 unit plans ───────────────────────────────────────────────
    30: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T04-3BHK-01", "T04-3BHK-02"]},
    31: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T04-3BHK-03"]},
    32: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T04-4BHK-03"]},
    33: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T04-4BHK-03-FL36"]},
    34: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T04-4BHK-DUPLEX-01"]},

    # ── Tower 05 overall floor plans ──────────────────────────────────────
    35: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T05", "title": "T05 typical floor plan"},
    36: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T05", "title": "T05 refuge floor plan 7 15 22 29"},
    37: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T05", "title": "T05 refuge floor plan 36"},
    38: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T05", "title": "T05 duplex floor plan 39 lower"},
    39: {"asset_level": "tower", "asset_type": "floor_plan", "tower": "T05", "title": "T05 duplex floor plan 40 upper"},

    # ── Tower 05 unit plans ───────────────────────────────────────────────
    40: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T05-3BHK-01"]},
    41: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T05-3BHK-02"]},
    42: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T05-3BHK-03"]},
    43: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T05-STUDIO-01-FL36", "T05-STUDIO-01-REFUGE"]},
    44: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T05-4BHK-DUPLEX-02"]},
    45: {"asset_level": "configuration", "asset_type": "floor_plan", "configs": ["T05-4BHK-DUPLEX-03"]},

    # ── Amenities ─────────────────────────────────────────────────────────
    46: {"asset_level": "building", "asset_type": "amenity", "title": "Eco deck pool"},
    47: {"asset_level": "building", "asset_type": "amenity", "title": "Eco deck courtyard"},
    48: {"asset_level": "building", "asset_type": "amenity", "title": "Eco deck jogging track"},
    49: {"asset_level": "building", "asset_type": "amenity", "title": "Bowling alley"},
    50: {"asset_level": "building", "asset_type": "amenity", "title": "Cafe"},
    51: {"asset_level": "building", "asset_type": "amenity", "title": "Banquet hall"},
    52: {"asset_level": "building", "asset_type": "amenity", "title": "Swimming pool"},
    53: {"asset_level": "building", "asset_type": "amenity", "title": "Indoor kids play area"},
    54: {"asset_level": "building", "asset_type": "amenity", "title": "Outdoor kids play area"},
    55: {"asset_level": "building", "asset_type": "amenity", "title": "Spa and wellness"},
    # p56: payment plan — skip
    # p57: back cover — skip
}


# ── helpers ───────────────────────────────────────────────────────────────────

def get_conn():
    env = {}
    env_path = Path(__file__).parent.parent / "docker" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "localhost"),
        port=int(env.get("POSTGRES_PORT", 5432)),
        dbname=env.get("POSTGRES_DB", "realdeal_os"),
        user=env.get("POSTGRES_USER", "realdeal_admin"),
        password=env.get("POSTGRES_PASSWORD", ""),
    )


def page_filename(page_num, entry):
    level = entry["asset_level"]
    atype = entry["asset_type"]
    if level == "tower":
        slug = entry["tower"].lower() + "-" + atype + "-p" + str(page_num)
    elif level == "configuration":
        first_cfg = entry["configs"][0].lower()
        slug = first_cfg + "-" + atype + "-p" + str(page_num)
    else:
        title_slug = entry.get("title", atype).lower().replace(" ", "-")[:40]
        slug = "building-" + title_slug + "-p" + str(page_num)
    return slug + ".png"


def render_page(pdf_doc, page_num, out_path):
    page = pdf_doc[page_num - 1]  # 0-indexed
    mat = fitz.Matrix(RENDER_SCALE, RENDER_SCALE)
    pix = page.get_pixmap(matrix=mat)
    pix.save(str(out_path))
    return out_path.stat().st_size


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


ASSET_TYPE_TO_MEDIA_TYPE = {
    "floor_plan":   "floor_plan",
    "exterior":     "photo",
    "interior":     "photo",
    "amenity":      "photo",
    "master_layout":"photo",
    "location_map": "photo",
    "video":        "video",
    "brochure":     "document",
}


def build_insert_rows(page_num, entry, file_path, file_hash, file_size):
    """Returns list of dicts — one per config_type (or one for building/tower pages)."""
    atype = entry["asset_type"]
    base = {
        "building_id":    DLF_BUILDING_ID,
        "asset_type":     atype,
        "asset_level":    entry["asset_level"],
        "media_type":     ASSET_TYPE_TO_MEDIA_TYPE.get(atype, "photo"),
        "source":         "brochure_extract",
        "file_path":      str(file_path),
        "sha256_hash":    file_hash,
        "file_size_bytes": file_size,
        "reviewed":       False,
        "brochure_page":  page_num,
    }
    if entry["asset_level"] == "configuration":
        rows = []
        for cfg in entry["configs"]:
            row = dict(base)
            row["configuration_type"] = cfg
            row["alt_text"] = cfg + " floor plan"
            rows.append(row)
        return rows
    else:
        row = dict(base)
        title = entry.get("title", atype)
        row["alt_text"] = title
        row["title"] = title
        if entry["asset_level"] == "tower":
            # store tower in alt_text; no separate tower_code column on media_assets
            row["alt_text"] = entry.get("tower", "") + " " + title
        return [row]


def insert_rows(conn, rows, dry_run):
    inserted = 0
    skipped = 0
    with conn.cursor() as cur:
        for row in rows:
            # skip if exact (file_path, configuration_type) already exists
            cur.execute(
                "SELECT id FROM media_assets WHERE file_path = %s AND configuration_type IS NOT DISTINCT FROM %s",
                (row["file_path"], row.get("configuration_type")),
            )
            if cur.fetchone():
                skipped += 1
                continue
            if dry_run:
                inserted += 1
                continue
            cols = list(row.keys())
            vals = [row[c] for c in cols]
            placeholders = ", ".join(["%s"] * len(cols))
            col_str = ", ".join(cols)
            cur.execute(f"INSERT INTO media_assets ({col_str}) VALUES ({placeholders})", vals)
            inserted += 1
    if not dry_run:
        conn.commit()
    return inserted, skipped


# ── main ──────────────────────────────────────────────────────────────────────

def run(apply=False, single_page=None):
    if not BROCHURE_PATH.exists():
        print(f"ERROR: brochure not found: {BROCHURE_PATH}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pages = {single_page: PAGE_MAP[single_page]} if single_page else PAGE_MAP
    conn = get_conn()

    pdf = fitz.open(str(BROCHURE_PATH))
    total_inserted = total_skipped = total_files = 0

    print(f"\n{'[APPLY]' if apply else '[DRY-RUN]'} DLF Westpark brochure extractor")
    print(f"  PDF: {BROCHURE_PATH.name} ({pdf.page_count} pages)")
    print(f"  Output: {OUTPUT_DIR}\n")

    for page_num, entry in sorted(pages.items()):
        fname = page_filename(page_num, entry)
        out_path = OUTPUT_DIR / fname
        level = entry["asset_level"]
        atype = entry["asset_type"]
        label = entry.get("title") or ", ".join(entry.get("configs", []))

        if apply:
            size = render_page(pdf, page_num, out_path)
            fhash = file_sha256(out_path)
            total_files += 1
        else:
            size = 0
            fhash = "dry-run"
            out_path = OUTPUT_DIR / fname

        rows = build_insert_rows(page_num, entry, out_path, fhash, size)
        ins, skp = insert_rows(conn, rows, dry_run=not apply)
        total_inserted += ins
        total_skipped += skp

        status = f"+{ins}" if ins else f"skip({skp})"
        print(f"  p{page_num:02d}  [{level:<13}] [{atype:<12}]  {label:<45}  {status}")

    pdf.close()
    conn.close()

    print(f"\n{'Files rendered' if apply else 'Files would render'}: {len(pages)}")
    print(f"DB rows {'inserted' if apply else 'would insert'}: {total_inserted}  skipped: {total_skipped}")
    if not apply:
        print("\nRe-run with --apply to write files + DB rows.")


def revert():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM media_assets
            WHERE building_id = %s AND source = 'brochure' AND brochure_page IS NOT NULL
        """, (DLF_BUILDING_ID,))
        n = cur.rowcount
    conn.commit()
    conn.close()
    print(f"Deleted {n} brochure media_asset rows (files on disk untouched).")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply",  action="store_true")
    p.add_argument("--revert", action="store_true")
    p.add_argument("--page",   type=int, default=None, help="Process single page (1-indexed)")
    args = p.parse_args()

    if args.page and args.page not in PAGE_MAP:
        print(f"ERROR: page {args.page} not in PAGE_MAP (skipped or unmapped).")
        sys.exit(1)

    if args.revert:
        revert()
    else:
        run(apply=args.apply, single_page=args.page)


if __name__ == "__main__":
    main()
