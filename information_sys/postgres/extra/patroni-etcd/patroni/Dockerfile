FROM postgres:17-bookworm

ARG PATRONI_VERSION=4.1.5

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
    && python3 -m venv /opt/patroni \
    && /opt/patroni/bin/pip install --no-cache-dir "patroni[psycopg3,etcd3]==${PATRONI_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/patroni/bin:/usr/lib/postgresql/17/bin:${PATH}" \
    PATRONI_CONFIG_FILE=/etc/patroni/patroni.yml

COPY patroni/patroni.yml /etc/patroni/patroni.yml
COPY patroni/patroni-entrypoint.sh /usr/local/bin/patroni-entrypoint.sh
COPY patroni/post-bootstrap.sh /usr/local/bin/post-bootstrap.sh
COPY patroni/bootstrap.sql /opt/warehouse/bootstrap.sql

RUN chmod 0755 /usr/local/bin/patroni-entrypoint.sh /usr/local/bin/post-bootstrap.sh \
    && mkdir -p /var/lib/postgresql/patroni \
    && chown -R postgres:postgres /var/lib/postgresql/patroni /opt/warehouse

EXPOSE 5432 8008

ENTRYPOINT ["/usr/local/bin/patroni-entrypoint.sh"]
CMD ["patroni", "/etc/patroni/patroni.yml"]
