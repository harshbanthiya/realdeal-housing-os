#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/docker/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE"
  echo "Create it from docker/.env.example before checking the database."
  exit 1
fi

DOCKER_BIN="${DOCKER_BIN:-docker}"
if ! command -v "$DOCKER_BIN" >/dev/null 2>&1; then
  if [ -x /usr/local/bin/docker ]; then
    DOCKER_BIN=/usr/local/bin/docker
  elif [ -x /Applications/Docker.app/Contents/Resources/bin/docker ]; then
    DOCKER_BIN=/Applications/Docker.app/Contents/Resources/bin/docker
  else
    echo "Docker CLI was not found. Start Docker Desktop and try again."
    exit 1
  fi
fi

read_env_value() {
  local key="$1"
  grep "^${key}=" "$ENV_FILE" | head -n 1 | cut -d '=' -f2-
}

POSTGRES_USER="$(read_env_value POSTGRES_USER)"
POSTGRES_PASSWORD="$(read_env_value POSTGRES_PASSWORD)"
POSTGRES_DB="$(read_env_value POSTGRES_DB)"

if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
  echo "Missing POSTGRES_USER, POSTGRES_PASSWORD, or POSTGRES_DB in $ENV_FILE"
  exit 1
fi

DB_NAME="${POSTGRES_DB:-realdeal_os}"
EXPECTED_TABLES="'contacts','buildings','inventory','media_assets','content_items','interactions','tasks','import_batches','contact_import_rows','contact_aliases','contact_property_hints','contact_duplicate_candidates','source_files','contact_methods','lead_requirements','inventory_import_rows','import_review_items','review_action_log','canonical_merge_batches','canonical_merge_links'"
EXPECTED_VIEWS="'vw_import_contact_review','vw_duplicate_review','vw_inventory_import_review','vw_lead_requirements_review','vw_review_dashboard_summary','vw_review_contact_methods','vw_review_business_leads','vw_review_duplicate_candidates','vw_review_queue','vw_review_batch_sources','vw_canonical_merge_batches','vw_canonical_merge_links'"

echo "Checking Real Deal OS tables in database: $DB_NAME"

"$DOCKER_BIN" exec -e PGPASSWORD="$POSTGRES_PASSWORD" realdeal-postgres \
  psql -U "$POSTGRES_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "
WITH expected(table_name) AS (
  VALUES
    ('contacts'),
    ('buildings'),
    ('inventory'),
    ('media_assets'),
    ('content_items'),
    ('interactions'),
    ('tasks'),
    ('import_batches'),
    ('contact_import_rows'),
    ('contact_aliases'),
    ('contact_property_hints'),
    ('contact_duplicate_candidates'),
    ('source_files'),
    ('contact_methods'),
    ('lead_requirements'),
    ('inventory_import_rows'),
    ('import_review_items'),
    ('review_action_log'),
    ('canonical_merge_batches'),
    ('canonical_merge_links')
)
SELECT
  expected.table_name,
  CASE WHEN tables.table_name IS NULL THEN 'missing' ELSE 'ok' END AS status
FROM expected
LEFT JOIN information_schema.tables tables
  ON tables.table_schema = 'public'
 AND tables.table_name = expected.table_name
ORDER BY expected.table_name;
"

MISSING_COUNT="$("$DOCKER_BIN" exec -e PGPASSWORD="$POSTGRES_PASSWORD" realdeal-postgres \
  psql -U "$POSTGRES_USER" -d "$DB_NAME" -At -v ON_ERROR_STOP=1 -c "
WITH expected(table_name) AS (
  SELECT unnest(ARRAY[$EXPECTED_TABLES])
)
SELECT count(*)
FROM expected
LEFT JOIN information_schema.tables tables
  ON tables.table_schema = 'public'
 AND tables.table_name = expected.table_name
WHERE tables.table_name IS NULL;
")"

if [ "$MISSING_COUNT" != "0" ]; then
  echo "Database check failed: $MISSING_COUNT expected table(s) are missing."
  exit 1
fi

echo "Checking Real Deal OS review views in database: $DB_NAME"

"$DOCKER_BIN" exec -e PGPASSWORD="$POSTGRES_PASSWORD" realdeal-postgres \
  psql -U "$POSTGRES_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "
WITH expected(view_name) AS (
  VALUES
    ('vw_import_contact_review'),
    ('vw_duplicate_review'),
    ('vw_inventory_import_review'),
    ('vw_lead_requirements_review'),
    ('vw_review_dashboard_summary'),
    ('vw_review_contact_methods'),
    ('vw_review_business_leads'),
    ('vw_review_duplicate_candidates'),
    ('vw_review_queue'),
    ('vw_review_batch_sources'),
    ('vw_canonical_merge_batches'),
    ('vw_canonical_merge_links')
)
SELECT
  expected.view_name,
  CASE WHEN views.table_name IS NULL THEN 'missing' ELSE 'ok' END AS status
FROM expected
LEFT JOIN information_schema.views views
  ON views.table_schema = 'public'
 AND views.table_name = expected.view_name
ORDER BY expected.view_name;
"

MISSING_VIEW_COUNT="$("$DOCKER_BIN" exec -e PGPASSWORD="$POSTGRES_PASSWORD" realdeal-postgres \
  psql -U "$POSTGRES_USER" -d "$DB_NAME" -At -v ON_ERROR_STOP=1 -c "
WITH expected(view_name) AS (
  SELECT unnest(ARRAY[$EXPECTED_VIEWS])
)
SELECT count(*)
FROM expected
LEFT JOIN information_schema.views views
  ON views.table_schema = 'public'
 AND views.table_name = expected.view_name
WHERE views.table_name IS NULL;
")"

if [ "$MISSING_VIEW_COUNT" != "0" ]; then
  echo "Database check failed: $MISSING_VIEW_COUNT expected view(s) are missing."
  exit 1
fi

echo "Database check passed: all expected Real Deal OS tables and views exist."
