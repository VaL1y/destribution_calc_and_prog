#!/usr/bin/env bash
set -Eeuo pipefail

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=replication_password="$REPLICATION_PASSWORD" <<'SQL'
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD :'replication_password';
SELECT pg_create_physical_replication_slot('standby_1');
SQL

if [ "${SYNC_MODE:-off}" = "on" ]; then
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "ALTER SYSTEM SET synchronous_standby_names TO 'FIRST 1 (pg_standby)'"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "ALTER SYSTEM SET synchronous_commit TO 'remote_apply'"
fi

cat >> "$PGDATA/pg_hba.conf" <<'HBA'
host replication replicator 0.0.0.0/0 scram-sha-256
HBA
