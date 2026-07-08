"""Worker harness: run logging + findings queue.

Workers are deterministic-first: pure SQL against local Postgres, zero external
dependencies, so they run every day even when Claude/LLM usage is exhausted.
LLM steps are optional add-ons via _llm.py and skip gracefully without a key.
Workers NEVER write canonical tables — only worker_runs / worker_findings.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import jsonb_lit, run_psql, sql_literal  # noqa: E402


def q(sql: str) -> list[list[str]]:
    code, out = run_psql(sql)
    if code != 0:
        raise RuntimeError(out)
    return [line.split("|") for line in out.splitlines() if line]


def one(sql: str) -> str:
    rows = q(sql)
    return rows[0][0] if rows and rows[0] else ""


def finding(worker: str, kind: str, dedupe_key: str, title: str,
            detail: dict | None = None, severity: str = "info") -> None:
    """Upsert a finding; re-runs refresh last_seen_at instead of duplicating."""
    q(f"""
        INSERT INTO worker_findings (worker, kind, dedupe_key, title, detail, severity)
        VALUES ({sql_literal(worker)}, {sql_literal(kind)}, {sql_literal(dedupe_key)},
                {sql_literal(title)}, {jsonb_lit(detail or {})}, {sql_literal(severity)})
        ON CONFLICT (dedupe_key) DO UPDATE SET
          title = EXCLUDED.title,
          detail = EXCLUDED.detail,
          severity = EXCLUDED.severity,
          last_seen_at = now()
    """)


def log_run(worker: str, fn) -> bool:
    """Run fn() -> (summary, items_found, detail_dict); log to worker_runs."""
    run_id = one(f"INSERT INTO worker_runs (worker) VALUES ({sql_literal(worker)}) RETURNING id")
    try:
        summary, items, detail = fn()
        q(f"""UPDATE worker_runs SET finished_at = now(), status = 'ok',
              summary = {sql_literal(summary)}, items_found = {int(items)},
              detail = {jsonb_lit(detail)} WHERE id = {run_id}""")
        print(f"[ok] {worker}: {summary}")
        return True
    except Exception:
        err = traceback.format_exc()[-1500:]
        q(f"""UPDATE worker_runs SET finished_at = now(), status = 'error',
              summary = {sql_literal(err.splitlines()[-1])},
              detail = {jsonb_lit({'traceback': err})} WHERE id = {run_id}""")
        print(f"[error] {worker}: {err.splitlines()[-1]}", file=sys.stderr)
        return False
