#!/usr/bin/env python3
"""Migrate scripts/ to use shared _db.py instead of copy-pasted helpers.

Removes local definitions of: read_env_value, sql_literal, lit, jsonb_lit,
run_psql, psql, scalar — and adds `from _db import ...` in their place.
Also drops `ENV_FILE = ...` and `import subprocess` when no longer referenced.

Dry-run by default; --apply to write.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
DB_HELPERS = {"read_env_value", "sql_literal", "lit", "jsonb_lit", "run_psql", "psql", "scalar"}

# run_psql variants with different return types cannot use the shared version
_VARIANT_RUN_PSQL = re.compile(
    r"^def run_psql\b.+-> (?:int|list\[)", re.MULTILINE
)


def detect_helpers(source: str) -> set[str]:
    found = {
        name for name in DB_HELPERS
        if re.search(rf"^def {re.escape(name)}\b", source, re.MULTILINE)
    }
    # Skip run_psql if the signature differs from -> tuple[int, str]
    if "run_psql" in found and _VARIANT_RUN_PSQL.search(source):
        found.discard("run_psql")
    return found


def remove_functions(source: str, names: set[str]) -> str:
    """Remove top-level function definitions by name using a line-state machine."""
    lines = source.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^def (\w+)\b", line)
        if m and m.group(1) in names:
            # Eat trailing blank lines already in result
            while result and result[-1].strip() == "":
                result.pop()
            i += 1
            # Skip function body (indented lines + blank lines within)
            while i < len(lines):
                l = lines[i]
                if l == "" or l.startswith(" ") or l.startswith("\t"):
                    i += 1
                else:
                    break
        else:
            result.append(line)
            i += 1
    return "\n".join(result)


def remove_env_file_line(source: str) -> str:
    """Drop `ENV_FILE = ...` only if ENV_FILE no longer appears in source."""
    after = re.sub(r"^ENV_FILE = [^\n]+\n", "", source, flags=re.MULTILINE)
    if "ENV_FILE" in after:
        return source  # still needed
    return after


def remove_subprocess_import(source: str) -> str:
    """Drop `import subprocess` if subprocess is no longer referenced."""
    candidate = re.sub(r"^import subprocess\n", "", source, flags=re.MULTILINE)
    if "subprocess" in candidate:
        return source  # still needed
    return candidate


def add_db_import(source: str, helpers: set[str]) -> str:
    """Insert `from _db import ...` right after `from __future__ import annotations`."""
    names = ", ".join(sorted(helpers))
    import_line = f"from _db import {names}"
    return re.sub(
        r"(from __future__ import annotations\n)",
        rf"\1{import_line}\n",
        source,
        count=1,
    )


def collapse_blank_lines(source: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", source)


def migrate(path: Path, apply: bool) -> tuple[int, str]:
    source = path.read_text(encoding="utf-8")
    helpers = detect_helpers(source)
    if not helpers:
        return 0, "skip"

    new = remove_functions(source, helpers)
    new = remove_env_file_line(new)
    new = remove_subprocess_import(new)
    new = add_db_import(new, helpers)
    new = collapse_blank_lines(new)

    saved = len(source.splitlines()) - len(new.splitlines())
    if apply:
        path.write_text(new, encoding="utf-8")
        return saved, "migrated"
    return saved, f"dry-run ({saved:+d} lines)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("files", nargs="*", help="Specific files (default: all scripts/*.py)")
    args = ap.parse_args()

    targets = (
        [Path(f) for f in args.files]
        if args.files
        else sorted(SCRIPTS_DIR.glob("*.py"))
    )
    # Never migrate _db.py or _migrate_to_db.py itself
    targets = [p for p in targets if p.name not in ("_db.py", "_migrate_to_db.py")]

    total_saved = 0
    migrated = 0
    for path in targets:
        saved, status = migrate(path, apply=args.apply)
        if status != "skip":
            print(f"  {status:30s}  {path.name}  ({saved:+d} lines)")
            total_saved += saved
            migrated += 1

    verb = "Migrated" if args.apply else "Would migrate"
    print(f"\n{verb} {migrated} files, {total_saved:+d} lines total.")
    if not args.apply:
        print("Re-run with --apply to write.")


if __name__ == "__main__":
    main()
