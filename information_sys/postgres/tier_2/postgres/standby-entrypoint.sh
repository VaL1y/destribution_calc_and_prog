#!/usr/bin/env bash
set -Eeuo pipefail

export PGPASSWORD="$REPLICATION_PASSWORD"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  mkdir -p "$PGDATA"
  chown -R postgres:postgres "$PGDATA"
  chmod 0700 "$PGDATA"

  until pg_isready -h "$PRIMARY_HOST" -p 5432 -U "$POSTGRES_USER"; do
    echo "Waiting for primary $PRIMARY_HOST"
    sleep 1
  done

  gosu postgres pg_basebackup \
    --dbname="host=$PRIMARY_HOST port=5432 user=replicator password=$REPLICATION_PASSWORD application_name=pg_standby" \
    --pgdata="$PGDATA" \
    --format=plain \
    --wal-method=stream \
    --write-recovery-conf \
    --slot=standby_1
fi

chown -R postgres:postgres "$PGDATA"
chmod 0700 "$PGDATA"
exec gosu postgres postgres -D "$PGDATA" -c hot_standby=on
