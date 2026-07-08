"""Market Watch worker: intake for the daily market-watch loop.

Operator (or any capture flow) drops files — portal screenshots, saved pages,
IGR exports, price sheets — into imports/market_inbox/. This worker registers
each unseen file in source_files (sha256-deduped) and files an action finding
so parsing connects it to building intelligence.

Parse path per file type (next step, not this worker): XLS → scripts IGR bulk
parser; PDF → pdftotext/docling; screenshots → vision parse via _llm.py.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from _lib import finding, log_run, one, sql_literal

INBOX = Path(__file__).resolve().parents[1] / "imports" / "market_inbox"


def run() -> tuple[str, int, dict]:
    INBOX.mkdir(parents=True, exist_ok=True)
    new_files = 0
    skipped = 0
    for f in sorted(INBOX.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        if one(f"SELECT count(*) FROM source_files WHERE file_hash_sha256 = {sql_literal(sha)}") != "0":
            skipped += 1
            continue
        rel = str(f.relative_to(INBOX.parents[1]))
        src_id = one(f"""
            INSERT INTO source_files (original_file_name, stored_relative_path, file_ext,
                                      file_size_bytes, file_hash_sha256,
                                      detected_source_format, processing_status)
            VALUES ({sql_literal(f.name)}, {sql_literal(rel)}, {sql_literal(f.suffix.lstrip('.').lower())},
                    {f.stat().st_size}, {sql_literal(sha)}, 'market_inbox', 'pending')
            RETURNING id
        """)
        new_files += 1
        finding("market_watch", "new_market_file", f"mw:{sha[:16]}",
                f"New market file to parse: {f.name}",
                {"source_file_id": src_id, "path": rel, "ext": f.suffix.lower()},
                severity="action")
    return (f"{new_files} new files registered, {skipped} already known", new_files,
            {"new": new_files, "known": skipped, "inbox": str(INBOX)})


if __name__ == "__main__":
    log_run("market_watch", run)
