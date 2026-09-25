FROM postgres:17-bookworm

COPY primary-init.sh /docker-entrypoint-initdb.d/01-create-replicator.sh
COPY standby-entrypoint.sh /usr/local/bin/standby-entrypoint.sh

RUN chmod 0755 /docker-entrypoint-initdb.d/01-create-replicator.sh \
    /usr/local/bin/standby-entrypoint.sh
