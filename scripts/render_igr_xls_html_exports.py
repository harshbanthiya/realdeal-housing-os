#!/usr/bin/env python3
"""Render IGR .xls HTML exports as browser-friendly UTF-8 pages.

The IGR "xls" files are UTF-16 HTML table fragments. This script preserves the
raw table content, wraps each export in a searchable page, and creates an index.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "exports" / "igr_xls_rendered_html"
DEFAULT_INPUTS = [
    Path("/Users/sheeed/Downloads/SearchResult3 (3).xls"),
    Path("/Users/sheeed/Downloads/SearchResult3.xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (1).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (2).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (3).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (4).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (5).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (6).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (7).xls"),
    Path("/Users/sheeed/Downloads/SearchResult4 (8).xls"),
]


CSS = """
:root {
  color-scheme: light;
  --ink: #17211c;
  --muted: #66736c;
  --line: #d9e0dc;
  --paper: #fbfcfb;
  --accent: #096c60;
  --soft: #edf5f2;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans Devanagari", "Noto Sans", Arial, sans-serif;
}
header {
  position: sticky;
  top: 0;
  z-index: 5;
  border-bottom: 1px solid var(--line);
  background: rgba(251, 252, 251, 0.96);
  backdrop-filter: blur(10px);
  padding: 14px 18px 12px;
}
.crumb { color: var(--muted); font-size: 12px; margin-bottom: 4px; }
h1 { margin: 0; font-size: 20px; line-height: 1.25; }
.meta { margin-top: 6px; color: var(--muted); font-size: 12px; }
.tools { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-top: 12px; }
input[type="search"] {
  width: min(680px, 100%);
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 9px 10px;
  font: inherit;
  background: white;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.wrap { padding: 16px 18px 28px; }
.table-shell {
  overflow: auto;
  border: 1px solid var(--line);
  background: white;
  max-height: calc(100vh - 140px);
}
table {
  border-collapse: collapse !important;
  width: max-content !important;
  min-width: 100%;
  height: auto !important;
  font-size: 12px;
  line-height: 1.35;
}
th, td {
  border: 1px solid var(--line) !important;
  padding: 6px 8px;
  max-width: 520px;
  min-width: 80px;
  vertical-align: top;
  background: white;
}
th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--soft);
  color: #123d37;
  white-space: nowrap;
  text-align: left;
  font-weight: 650;
}
td:nth-child(2), td:nth-child(3), td:nth-child(4), td:nth-child(5),
th:nth-child(2), th:nth-child(3), th:nth-child(4), th:nth-child(5) {
  white-space: nowrap;
}
td:nth-child(10), td:nth-child(11), td:nth-child(12) {
  min-width: 360px;
}
tr[data-match="0"] { display: none; }
tr:hover td { background: #fffdf5; }
.count { color: var(--muted); font-size: 12px; }
.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
  margin-top: 18px;
}
.file-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: white;
  padding: 14px;
}
.file-card strong { display: block; margin-bottom: 8px; }
.file-card div { color: var(--muted); font-size: 12px; margin-top: 4px; }
"""


JS = """
const search = document.querySelector('#search');
const rows = Array.from(document.querySelectorAll('tbody tr'));
const count = document.querySelector('#visibleCount');
function applyFilter() {
  const q = (search?.value || '').trim().toLowerCase();
  let visible = 0;
  rows.forEach((row) => {
    const ok = !q || row.textContent.toLowerCase().includes(q);
    row.dataset.match = ok ? '1' : '0';
    if (ok) visible += 1;
  });
  if (count) count.textContent = `${visible} / ${rows.length} rows visible`;
}
search?.addEventListener('input', applyFilter);
applyFilter();
"""


def decode_export(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def slugify(name: str) -> str:
    stem = re.sub(r"\.xls$", "", name, flags=re.I)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-").lower()
    return slug or "igr-export"


def table_stats(fragment: str) -> tuple[int, int]:
    rows = re.findall(r"<tr\b", fragment, flags=re.I)
    headers = re.findall(r"<th\b", fragment, flags=re.I)
    return max(len(rows) - 1, 0), len(headers)


def normalise_fragment(fragment: str) -> str:
    # Preserve the raw table, but strip accidental XML/Excel metadata if it ever
    # appears before the first div/table.
    start = min([i for i in [fragment.lower().find("<div"), fragment.lower().find("<table")] if i >= 0] or [0])
    body = fragment[start:].strip()
    body = re.sub(r"<table\b", '<table data-igr-export="true"', body, count=1, flags=re.I)
    return body


def render_file(source: Path, output_dir: Path) -> dict[str, str | int]:
    fragment = normalise_fragment(decode_export(source))
    row_count, column_count = table_stats(fragment)
    out_name = f"{slugify(source.name)}.html"
    out_path = output_dir / out_name
    title = source.name
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <div class="crumb"><a href="index.html">IGR XLS rendered exports</a></div>
    <h1>{html.escape(title)}</h1>
    <div class="meta">{row_count} data rows · {column_count} columns · source: {html.escape(str(source))}</div>
    <div class="tools">
      <input id="search" type="search" placeholder="Search this file: flat no, doc no, Kalpataru, party name, rent, date...">
      <span id="visibleCount" class="count"></span>
    </div>
  </header>
  <main class="wrap">
    <div class="table-shell">
      {fragment}
    </div>
  </main>
  <script>{JS}</script>
</body>
</html>
"""
    out_path.write_text(page, encoding="utf-8")
    return {
        "source": str(source),
        "name": source.name,
        "output": str(out_path),
        "output_name": out_name,
        "rows": row_count,
        "columns": column_count,
    }


def render_index(items: list[dict[str, str | int]], output_dir: Path) -> Path:
    cards = "\n".join(
        f"""<a class="file-card" href="{html.escape(str(item["output_name"]))}">
  <strong>{html.escape(str(item["name"]))}</strong>
  <div>{item["rows"]} data rows · {item["columns"]} columns</div>
  <div>{html.escape(str(item["source"]))}</div>
</a>"""
        for item in items
    )
    total_rows = sum(int(item["rows"]) for item in items)
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IGR XLS rendered exports</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <h1>IGR XLS rendered exports</h1>
    <div class="meta">{len(items)} files · {total_rows} data rows · UTF-16 Excel/HTML converted to UTF-8 browser pages</div>
  </header>
  <main class="wrap">
    <div class="file-grid">
      {cards}
    </div>
  </main>
</body>
</html>
"""
    index_path = output_dir / "index.html"
    index_path.write_text(page, encoding="utf-8")
    return index_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render IGR HTML .xls exports for browser inspection.")
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    inputs = args.files or DEFAULT_INPUTS
    missing = [str(path) for path in inputs if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing input files: " + ", ".join(missing))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    items = [render_file(path, args.output_dir) for path in inputs]
    index = render_index(items, args.output_dir)
    print(f"Rendered {len(items)} files to {args.output_dir}")
    print(f"index: {index}")
    for item in items:
        print(f"{item['name']} -> {item['output']} ({item['rows']} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
