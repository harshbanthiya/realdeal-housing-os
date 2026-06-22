#!/usr/bin/env python3
"""Cleanup Phase 7.3 DLF lead-intake planning rows.

Dry-run by default. Deletes only rows tagged phase=7.3/source=dlf_lead_intake_plan_seed.
It refuses if any planned endpoint became active, any external-call flag is enabled,
any inbound lead exists from the seed tag, or any contact appears tagged to this seed.
"""

from __future__ import annotations
from _db import read_env_value, run_psql, scalar, sql_literal

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE = "7.3"
SOURCE = "dlf_lead_intake_plan_seed"

DELETE_ORDER = [
    "launch_inbound_lead_review_items",
    "launch_operator_daily_metrics",
    "launch_lead_attribution_rules",
    "launch_lead_field_mappings",
    "launch_lead_intake_endpoints",
    "launch_readiness_checks",
]
def where_clause(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return (
        f"{prefix}raw_context->>'phase' = {sql_literal(PHASE)} "
        f"AND {prefix}raw_context->>'source' = {sql_literal(SOURCE)}"
    )

def launch_filter(table_alias: str, launch_key: str) -> str:
    return (
        f"{table_alias}.launch_project_id IN (SELECT id FROM launch_projects "
        f"WHERE launch_key = {sql_literal(launch_key)})"
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup DLF lead-intake planning rows. Counts only.")
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

    active_endpoints = scalar(
        "SELECT count(*) FROM launch_lead_intake_endpoints e "
        f"WHERE {launch_filter('e', args.launch_key)} AND {where_clause('e')} "
        "AND e.endpoint_status = 'active';"
    )
    external_allowed = scalar(
        "SELECT count(*) FROM launch_lead_intake_endpoints e "
        f"WHERE {launch_filter('e', args.launch_key)} AND {where_clause('e')} "
        "AND e.external_call_allowed = true;"
    )
    inbound_leads = scalar(
        "SELECT count(*) FROM inbound_leads "
        f"WHERE raw_payload->>'phase' = {sql_literal(PHASE)} "
        f"AND raw_payload->>'source' = {sql_literal(SOURCE)};"
    )
    contacts_created = scalar(
        "SELECT count(*) FROM contacts "
        f"WHERE metadata->>'phase' = {sql_literal(PHASE)} "
        f"AND metadata->>'source' = {sql_literal(SOURCE)};"
    )

    if active_endpoints:
        print(f"Refusing cleanup: {active_endpoints} tagged endpoint(s) are active.")
        return 1
    if external_allowed:
        print(f"Refusing cleanup: {external_allowed} tagged endpoint(s) allow external calls.")
        return 1
    if inbound_leads:
        print(f"Refusing cleanup: {inbound_leads} inbound lead(s) exist from this source.")
        return 1
    if contacts_created:
        print(f"Refusing cleanup: {contacts_created} contact(s) appear tagged to this seed.")
        return 1

    mode = "APPLY" if (args.apply and args.real_ok) else "DRY-RUN"
    print(f"=== Phase 7.3 DLF lead-intake cleanup [{mode}] ===")
    print(f"launch_key={args.launch_key}")
    total = 0
    counts: list[tuple[str, int]] = []
    for table in DELETE_ORDER:
        n = scalar(
            f"SELECT count(*) FROM {table} t "
            f"WHERE {launch_filter('t', args.launch_key)} AND {where_clause('t')};"
        )
        counts.append((table, n))
        total += n
        print(f"  {table}: {n}")
    print(f"total_rows_in_scope={total}")
    print("guards: active_endpoints=0 external_call_allowed=0 inbound_leads_from_source=0 contacts_created_from_source=0")

    if not args.apply:
        print("DRY-RUN only: nothing deleted. Re-run with --apply --real-ok to delete.")
        return 0

    sql = ["BEGIN;"]
    for table, _ in counts:
        sql.append(
            f"DELETE FROM {table} t WHERE {launch_filter('t', args.launch_key)} AND {where_clause('t')};"
        )
    sql.append("COMMIT;")
    code, out = run_psql("\n".join(sql))
    if code != 0:
        print(f"Delete FAILED (rolled back): {out[:300]}")
        return 2
    print(f"DELETED {total} tagged Phase 7.3 row(s). No launch project, contacts, inbound leads, or earlier phase rows touched.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
