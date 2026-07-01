#!/usr/bin/env python3
"""
MIS Phase A — Disk scanner.

Walks /Volumes/RDH 5TB/ and indexes media files into media_assets.
All rows land with reviewed=false, source=disk_scan.
Building/unit inferred from folder path; ambiguous matches → review flag.

Usage:
  python scripts/scan_disk_media.py              # dry-run (default)
  python scripts/scan_disk_media.py --apply      # write to DB
  python scripts/scan_disk_media.py --path /Volumes/RDH\ 5TB/RDH\ DATA\ 2024/RDH\ ALL\ Footage
  python scripts/scan_disk_media.py --summary    # show counts only (no rows printed)
"""

import os
import sys
import hashlib
import argparse
import psycopg2
from pathlib import Path
from datetime import datetime

# ── config ────────────────────────────────────────────────────────────────────

SCAN_ROOT = Path("/Volumes/RDH 5TB")

MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tiff", ".tif",
    ".mp4", ".mov", ".avi", ".mkv", ".m4v",
    ".pdf",
}

# folders to skip entirely
SKIP_DIRS = {
    ".Spotlight-V100", ".fseventsd", ".Trashes", "._",
    "exports", "backups", "secrets",
}

PHASE = "MIS-A"

# ── DB ────────────────────────────────────────────────────────────────────────

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

# ── building lookup ───────────────────────────────────────────────────────────

def load_buildings(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, NULL AS building_code FROM buildings")
        return cur.fetchall()

def load_duplicate_map(conn):
    """Returns {duplicate_id: canonical_id} for all strong/pending dedup candidates."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT duplicate_building_id, canonical_building_id
            FROM building_duplicate_candidates
            WHERE status NOT IN ('rejected', 'skipped')
        """)
        return {row[0]: row[1] for row in cur.fetchall()}

def load_units(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, building_id, unit_number, wing FROM building_units")
        return cur.fetchall()

def infer_building(path_parts, buildings, duplicate_map):
    """Return (building_id, match_type) or (None, 'ambiguous'/'no_match').
    Resolves ambiguity by collapsing duplicate IDs to their canonical.
    """
    candidates = []
    for bid, dname, bcode in buildings:
        tokens = set((dname or "").lower().split()) | set((bcode or "").lower().split())
        for part in path_parts:
            part_lower = part.lower()
            if any(tok in part_lower for tok in tokens if len(tok) > 3):
                # remap duplicate → canonical before appending
                canonical = duplicate_map.get(bid, bid)
                candidates.append(canonical)
                break
    candidates = list(dict.fromkeys(candidates))  # dedup, preserve order
    if len(candidates) == 1:
        return candidates[0], "path_match"
    if len(candidates) > 1:
        return None, "ambiguous"
    return None, "no_match"

def infer_unit(path_parts, building_id, units):
    """Return (unit_id, match_type) or (None, reason)."""
    for uid, bid, unum, wing in units:
        if bid != building_id:
            continue
        label = f"{wing}-{unum}".lower() if wing else unum.lower()
        for part in path_parts:
            if label.replace("-", " ") in part.lower() or label in part.lower().replace(" ", "-"):
                return uid, "path_match"
    return None, "no_match"

# ── asset inference ───────────────────────────────────────────────────────────

LEVEL_HINTS = {
    "building": "building", "exteriors": "building", "amenities": "building",
    "lobby": "building", "master": "building", "common": "building",
    "tower": "tower", "floor": "tower",
    "show": "configuration", "sample": "configuration", "stock": "configuration",
    "3bhk": "configuration", "2bhk": "configuration", "4bhk": "configuration",
    "1bhk": "configuration",
}

TYPE_HINTS = {
    "floor_plan": "floor_plan", "floorplan": "floor_plan", "plan": "floor_plan",
    "exterior": "exterior", "outside": "exterior", "facade": "exterior",
    "interior": "interior", "inside": "interior",
    "amenity": "amenity", "amenities": "amenity", "gym": "amenity",
    "pool": "amenity", "clubhouse": "amenity",
    "master_layout": "master_layout", "master": "master_layout", "layout": "master_layout",
    "brochure": "brochure",
}

EXT_TO_MEDIA_TYPE = {
    ".jpg": "photo", ".jpeg": "photo", ".png": "photo",
    ".webp": "photo", ".heic": "photo", ".heif": "photo",
    ".tiff": "photo", ".tif": "photo",
    ".mp4": "video", ".mov": "video", ".avi": "video",
    ".mkv": "video", ".m4v": "video",
    ".pdf": "document",
}

def infer_asset_attrs(path: Path, has_unit: bool):
    parts_lower = [p.lower() for p in path.parts]
    name_lower = path.stem.lower()
    all_tokens = parts_lower + [name_lower]

    asset_level = "unit" if has_unit else None
    for token_set in all_tokens:
        for hint, level in LEVEL_HINTS.items():
            if hint in token_set:
                asset_level = asset_level or level
                break

    asset_type = None
    for token_set in all_tokens:
        for hint, atype in TYPE_HINTS.items():
            if hint in token_set:
                asset_type = atype
                break
        if asset_type:
            break

    ext = path.suffix.lower()
    if ext in (".mp4", ".mov", ".avi", ".mkv", ".m4v"):
        asset_type = asset_type or "video"
        asset_level = asset_level or "building"
    elif ext == ".pdf":
        asset_type = asset_type or "brochure"
        asset_level = asset_level or "building"

    media_type = EXT_TO_MEDIA_TYPE.get(ext, "other")
    return asset_level, asset_type, media_type

def sha256_first_mb(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(1024 * 1024))
    return h.hexdigest()

# ── gate flags ────────────────────────────────────────────────────────────────

GATE_AMBIGUOUS_BUILDING = "PATH_BUILDING_MATCH_AMBIGUOUS"
GATE_NO_BUILDING = "PATH_BUILDING_NO_MATCH"
GATE_NO_UNIT = "PATH_UNIT_MATCH_FAILED"
GATE_TYPE_UNCLEAR = "ASSET_TYPE_UNCLEAR"

# ── scan ──────────────────────────────────────────────────────────────────────

def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part.startswith("._"):
            return True
        if part in SKIP_DIRS:
            return True
    return False

def scan(root: Path, buildings, units, duplicate_map, dry_run: bool, conn, summary_only: bool):
    counts = {"scanned": 0, "inserted": 0, "skipped": 0, "gates": {}}
    seen_hashes = set()

    with conn.cursor() as cur:
        cur.execute("SELECT sha256_hash FROM media_assets WHERE sha256_hash IS NOT NULL AND source = 'disk_scan'")
        seen_hashes = {row[0] for row in cur.fetchall()}

    insert_sql = """
        INSERT INTO media_assets (
          file_path, building_id, unit_id, media_type,
          asset_level, asset_type, source,
          configuration_type, sha256_hash, file_size_bytes,
          reviewed, upload_status, virtual_stage_status,
          review_notes, scan_phase, tags,
          title, status, metadata
        ) VALUES (
          %s, %s, %s, %s,
          %s, %s, 'disk_scan',
          %s, %s, %s,
          false, 'local_only', 'none',
          %s, %s, '{}',
          %s, 'raw', '{}'
        )
        ON CONFLICT DO NOTHING
    """

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith("._")]
        for fname in filenames:
            if fname.startswith("._") or fname.startswith("."):
                continue
            fpath = Path(dirpath) / fname
            if should_skip(fpath):
                continue
            ext = fpath.suffix.lower()
            if ext not in MEDIA_EXTENSIONS:
                continue

            counts["scanned"] += 1
            try:
                fsize = fpath.stat().st_size
                fhash = sha256_first_mb(fpath)
            except (OSError, PermissionError):
                counts["skipped"] += 1
                continue

            if fhash in seen_hashes:
                counts["skipped"] += 1
                continue

            rel_parts = fpath.relative_to(root).parts
            building_id, bm_type = infer_building(rel_parts, buildings, duplicate_map)
            unit_id, um_type = (None, "skipped")
            if building_id:
                unit_id, um_type = infer_unit(rel_parts, building_id, units)

            asset_level, asset_type, media_type = infer_asset_attrs(fpath, unit_id is not None)

            gate_flags = []
            if bm_type == "ambiguous":
                gate_flags.append(GATE_AMBIGUOUS_BUILDING)
            elif bm_type == "no_match":
                gate_flags.append(GATE_NO_BUILDING)
            if building_id and um_type == "no_match" and asset_level == "unit":
                gate_flags.append(GATE_NO_UNIT)
            if asset_type is None:
                gate_flags.append(GATE_TYPE_UNCLEAR)

            review_notes = "; ".join(gate_flags) if gate_flags else None
            for g in gate_flags:
                counts["gates"][g] = counts["gates"].get(g, 0) + 1

            title = fpath.stem.replace("_", " ").replace("-", " ")

            if not summary_only:
                status = "DRY" if dry_run else "INSERT"
                print(f"  [{status}] {str(fpath.relative_to(root))[:80]}")
                if gate_flags:
                    print(f"         gates: {', '.join(gate_flags)}")

            if not dry_run:
                with conn.cursor() as cur:
                    cur.execute(insert_sql, (
                        str(fpath), building_id, unit_id, media_type,
                        asset_level, asset_type,
                        None,  # configuration_type — set during review
                        fhash, fsize,
                        review_notes, PHASE,
                        title,
                    ))
                conn.commit()
                seen_hashes.add(fhash)

            counts["inserted"] += 1

    return counts

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="Write to DB (default: dry-run)")
    p.add_argument("--path", default=str(SCAN_ROOT), help="Root path to scan")
    p.add_argument("--summary", action="store_true", help="Counts only, no per-file output")
    args = p.parse_args()

    dry_run = not args.apply
    scan_root = Path(args.path)

    if not scan_root.exists():
        print(f"ERROR: scan root not found: {scan_root}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'DRY RUN — ' if dry_run else ''}MIS Phase A disk scan")
    print(f"Root: {scan_root}\n")

    conn = get_conn()
    buildings = load_buildings(conn)
    units = load_units(conn)
    duplicate_map = load_duplicate_map(conn)
    print(f"Loaded {len(buildings)} buildings, {len(units)} units, {len(duplicate_map)} duplicate mappings from DB\n")

    counts = scan(scan_root, buildings, units, duplicate_map, dry_run, conn, args.summary)
    conn.close()

    print(f"\n── Summary ──────────────────────────────────────")
    print(f"  Files found     : {counts['scanned']}")
    print(f"  {'Would insert' if dry_run else 'Inserted'}    : {counts['inserted']}")
    print(f"  Skipped (dup/err): {counts['skipped']}")
    if counts["gates"]:
        print(f"  Gate flags:")
        for g, n in counts["gates"].items():
            print(f"    {g}: {n}")
    if dry_run:
        print("\nRe-run with --apply to write to DB.")


if __name__ == "__main__":
    main()
