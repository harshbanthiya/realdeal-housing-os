"""Shared DB helpers — docker exec psql. Import in all scripts."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parents[1] / "docker" / ".env"


def read_env_value(key: str) -> str:
    if not _ENV_FILE.exists():
        return ""
    prefix = f"{key}="
    with _ENV_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith(prefix):
                return line.rstrip("\n").split("=", 1)[1]
    return ""


def sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


# ponytail: alias for the 7 scripts that call lit() directly
lit = sql_literal


def jsonb_lit(obj: object) -> str:
    return sql_literal(json.dumps(obj)) + "::jsonb"


def run_psql(sql: str) -> tuple[int, str]:
    user = read_env_value("POSTGRES_USER")
    password = read_env_value("POSTGRES_PASSWORD")
    db_name = read_env_value("POSTGRES_DB")
    if not user or not password or not db_name:
        return 1, "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in docker/.env."
    cmd = [
        "docker", "exec", "-i", "-e", f"PGPASSWORD={password}",
        "realdeal-postgres", "psql", "-U", user, "-d", db_name,
        "-v", "ON_ERROR_STOP=1", "-At", "-F", "|",
    ]
    result = subprocess.run(cmd, input=sql, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout.strip() or result.stderr.strip())


# ponytail: older scripts use psql() returning int only
def psql(sql: str) -> int:
    return run_psql(sql)[0]


def scalar(sql: str) -> int:
    code, out = run_psql(sql)
    if code != 0 or not out:
        return 0
    try:
        return int(out.splitlines()[0])
    except ValueError:
        return 0
