#!/bin/sh
set -eu

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=postgres_user="$POSTGRES_USER" \
  --set=n8n_db="$N8N_DB" \
  --set=nocodb_db="$NOCODB_DB" <<'EOSQL'
SELECT format('CREATE DATABASE %I OWNER %I', :'n8n_db', :'postgres_user')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'n8n_db')\gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'nocodb_db', :'postgres_user')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'nocodb_db')\gexec
EOSQL

