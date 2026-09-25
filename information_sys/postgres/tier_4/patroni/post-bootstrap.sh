#!/bin/sh
set -eu

psql "$1" \
    --set=ON_ERROR_STOP=1 \
    --set=app_user="${POSTGRES_USER:?POSTGRES_USER is required}" \
    --set=app_password="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}" \
    --set=app_db="${POSTGRES_DB:?POSTGRES_DB is required}" \
    --file=/opt/warehouse/bootstrap.sql

