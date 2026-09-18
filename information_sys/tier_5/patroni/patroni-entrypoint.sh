#!/bin/sh
set -eu

data_dir="${PATRONI_POSTGRESQL_DATA_DIR:-/var/lib/postgresql/patroni}"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$data_dir" /var/run/postgresql
    chown -R postgres:postgres "$data_dir" /var/run/postgresql
    exec gosu postgres "$@"
fi

exec "$@"

