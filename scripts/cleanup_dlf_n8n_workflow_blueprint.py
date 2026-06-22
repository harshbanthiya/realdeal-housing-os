#!/usr/bin/env python3
"""Cleanup Phase 7.4 DLF n8n workflow blueprint rows.

Dry-run by default. Deletes only rows tagged phase=7.4/source=dlf_n8n_workflow_blueprint_seed.
It refuses if any workflow was built/activated, any external-call flag is enabled, any
test case executed, or any inbound lead exists from this blueprint source.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, scalar, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.4"
SOURCE = "dlf_n8n_workflow_blueprint_seed"

DELETE_ORDER = [
    "launch_n8n_review_items",
    "launch_n8n_test_cases",
    "launch_n8n_payload_schemas",
    "launch_n8n_workflow_nodes",
    "launch_n8n_workflow_blueprints",
]
def raw_where(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return (
        f"{prefix}raw_context->>'phase' = {sql_literal(PHASE)} "
        f"AND {prefix}raw_context->>'source' = {sql_literal(SOURCE)}"
    )

def table_scope(table: str, alias: str, launch_key: str) -> str:
    if table in ("launch_n8n_workflow_blueprints", "launch_n8n_review_items"):
        return (
            f"{alias}.launch_project_id IN (SELECT id FROM launch_projects WHERE launch_key = {sql_literal(launch_key)}) "
            f"AND {raw_where(alias)}"
        )
    return (
        f"{alias}.workflow_blueprint_id IN ("
        "SELECT b.id FROM launch_n8n_workflow_blueprints b "
        f"JOIN launch_projects p ON p.id = b.launch_project_id WHERE p.launch_key = {sql_literal(launch_key)} "
        f"AND {raw_where('b')}) AND {raw_where(alias)}"
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup DLF n8n workflow blueprint rows. Counts only.")
    parser.add_argument("--launch-key", default="dlf-westpark-andheri-west")
    parser.add_argument("--real-ok", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.real_ok:
        print("Refusing cleanup: --real-ok is required.")
        return 1

    project_count = scalar(f"SELECT count(*) FROM launch_projects WHERE launch_key = {sql_literal(args.launch_key)};")
    if project_count != 1:
        print("Refusing cleanup: expected exactly one launch project.")
        return 1

    built_or_active = scalar(
        "SELECT count(*) FROM launch_n8n_workflow_blueprints b "
        f"WHERE {table_scope('launch_n8n_workflow_blueprints', 'b', args.launch_key)} "
        "AND b.workflow_status IN ('built_in_n8n', 'active');"
    )
    active_activation = scalar(
        "SELECT count(*) FROM launch_n8n_workflow_blueprints b "
        f"WHERE {table_scope('launch_n8n_workflow_blueprints', 'b', args.launch_key)} "
        "AND b.activation_status = 'active';"
    )
    external_allowed = scalar(
        "SELECT count(*) FROM launch_n8n_workflow_blueprints b "
        f"WHERE {table_scope('launch_n8n_workflow_blueprints', 'b', args.launch_key)} "
        "AND b.external_call_allowed = true;"
    ) + scalar(
        "SELECT count(*) FROM launch_n8n_test_cases t "
        f"WHERE {table_scope('launch_n8n_test_cases', 't', args.launch_key)} "
        "AND t.external_call_allowed = true;"
    )
    executed_tests = scalar(
        "SELECT count(*) FROM launch_n8n_test_cases t "
        f"WHERE {table_scope('launch_n8n_test_cases', 't', args.launch_key)} "
        "AND t.test_status = 'executed';"
    )
    inbound_leads = scalar(
        "SELECT count(*) FROM inbound_leads "
        f"WHERE raw_payload->>'phase' = {sql_literal(PHASE)} "
        f"AND raw_payload->>'source' = {sql_literal(SOURCE)};"
    )

    if built_or_active:
        print(f"Refusing cleanup: {built_or_active} tagged workflow(s) are built or active.")
        return 1
    if active_activation:
        print(f"Refusing cleanup: {active_activation} tagged workflow(s) have active activation status.")
        return 1
    if external_allowed:
        print(f"Refusing cleanup: {external_allowed} tagged row(s) allow external calls.")
        return 1
    if executed_tests:
        print(f"Refusing cleanup: {executed_tests} tagged test case(s) were executed.")
        return 1
    if inbound_leads:
        print(f"Refusing cleanup: {inbound_leads} inbound lead(s) exist from this workflow source.")
        return 1

    mode = "APPLY" if (args.apply and args.real_ok) else "DRY-RUN"
    print(f"=== Phase 7.4 DLF n8n blueprint cleanup [{mode}] ===")
    print(f"launch_key={args.launch_key}")
    total = 0
    counts: list[tuple[str, int]] = []
    for table in DELETE_ORDER:
        n = scalar(f"SELECT count(*) FROM {table} t WHERE {table_scope(table, 't', args.launch_key)};")
        counts.append((table, n))
        total += n
        print(f"  {table}: {n}")
    print(f"total_rows_in_scope={total}")
    print("guards: built_or_active=0 active_activation=0 external_call_allowed=0 executed_tests=0 inbound_leads_from_source=0")

    if not args.apply:
        print("DRY-RUN only: nothing deleted. Re-run with --apply --real-ok to delete.")
        return 0

    sql = ["BEGIN;"]
    for table, _ in counts:
        sql.append(f"DELETE FROM {table} t WHERE {table_scope(table, 't', args.launch_key)};")
    sql.append("COMMIT;")
    code, out = run_psql("\n".join(sql))
    if code != 0:
        print(f"Delete FAILED (rolled back): {out[:300]}")
        return 2
    print(f"DELETED {total} tagged Phase 7.4 row(s). No earlier phase rows, inbound leads, contacts, or n8n workflows touched.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
