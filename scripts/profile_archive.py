#!/usr/bin/env python3
"""Safely profile all supported files inside a zip archive."""

from __future__ import annotations

import argparse
import json
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from profile_contact_file import profile_file
from source_format_utils import is_junk_archive_member, safe_stem


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def safe_extract_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo, dest_root: Path) -> Path:
    target = dest_root / member.filename
    resolved = target.resolve()
    try:
        resolved.relative_to(dest_root.resolve())
    except ValueError:
        raise ValueError(f"Unsafe archive path skipped: {member.filename}")
    if member.is_dir():
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(member) as src, resolved.open("wb") as dst:
        dst.write(src.read())
    return resolved


def profile_archive(zip_path: Path) -> Dict[str, object]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    profile_root = PROJECT_ROOT / "exports" / "archive_profiles" / safe_stem(zip_path)
    extract_root = profile_root / "extracted"
    extract_root.mkdir(parents=True, exist_ok=True)

    files: List[Dict[str, object]] = []
    skipped: List[str] = []
    by_extension: Counter = Counter()
    by_format: Counter = Counter()

    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir() or is_junk_archive_member(member.filename):
                skipped.append(member.filename)
                continue
            try:
                extracted = safe_extract_member(archive, member, extract_root)
            except ValueError:
                skipped.append(member.filename)
                continue

            extension = extracted.suffix.lower() or "(none)"
            by_extension[extension] += 1
            try:
                profile = profile_file(extracted)
            except Exception as exc:
                profile = {
                    "file_type": extension.lstrip(".") or "unknown",
                    "sheets": [],
                    "row_counts": {},
                    "columns": {},
                    "source_format": "profile_error",
                    "note": type(exc).__name__,
                }
            source_format = str(profile.get("source_format", "unknown"))
            by_format[source_format] += 1
            files.append(
                {
                    "archive_path": member.filename,
                    "extension": extension,
                    "file_size": member.file_size,
                    "detected_type": profile.get("file_type", ""),
                    "source_format": source_format,
                    "sheets": profile.get("sheets", []),
                    "row_counts": profile.get("row_counts", {}),
                    "columns": profile.get("columns", {}),
                    "note": profile.get("note", ""),
                    "extracted_path": str(extracted),
                }
            )

    report = {
        "archive": str(zip_path),
        "generated_at": timestamp,
        "extract_root": str(extract_root),
        "file_count": len(files),
        "skipped_count": len(skipped),
        "skipped_junk_count": len(skipped),
        "counts_by_extension": dict(sorted(by_extension.items())),
        "counts_by_source_format": dict(sorted(by_format.items())),
        "files": files,
    }

    contacts_out = PROJECT_ROOT / "exports" / "contacts"
    contacts_out.mkdir(parents=True, exist_ok=True)
    json_path = contacts_out / f"archive_profile_{timestamp}.json"
    md_path = contacts_out / f"archive_profile_{timestamp}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Archive Profile",
        "",
        f"Archive: `{zip_path.name}`",
        f"Files profiled: {len(files)}",
        f"Junk/skipped members: {len(skipped)}",
        "",
        "## Counts By Extension",
        "",
    ]
    for key, value in sorted(by_extension.items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Counts By Source Format", ""])
    for key, value in sorted(by_format.items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Files", ""])
    for item in files:
        row_bits = ", ".join(f"{k}={v}" for k, v in dict(item["row_counts"]).items())
        lines.append(f"- `{item['archive_path']}` | {item['extension']} | {item['file_size']} bytes | {item['source_format']} | {row_bits}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report["json_report"] = str(json_path)
    report["markdown_report"] = str(md_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely profile a zip archive of contact sources.")
    parser.add_argument("zip_path", help="Zip archive path.")
    args = parser.parse_args()

    zip_path = Path(args.zip_path)
    if not zip_path.exists():
        print("Archive not found.")
        return 1

    report = profile_archive(zip_path)
    print(f"Archive files profiled: {report['file_count']}")
    print(f"Junk/skipped members: {report['skipped_count']}")
    print("Counts by extension:")
    for key, value in report["counts_by_extension"].items():
        print(f"  {key}: {value}")
    print("Counts by source_format:")
    for key, value in report["counts_by_source_format"].items():
        print(f"  {key}: {value}")
    print(f"JSON report: {report['json_report']}")
    print(f"Markdown report: {report['markdown_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
