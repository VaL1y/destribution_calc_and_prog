# Запуск etcd-варианта

Скопируйте `.env.example` в `.env` на оба сервера. Сначала запустите `etcd-3` на
локальном сервере, затем `etcd-1` и `etcd-2` на удалённом, после чего запускайте
Patroni/PostgreSQL.

```bash
# local
docker compose --env-file .env -f compose.local.yml up -d etcd-3

# remote
docker compose --env-file .env -f compose.remote.yml up -d etcd-1 etcd-2
docker compose --env-file .env -f compose.remote.yml exec etcd-1 \
  etcdctl endpoint health --cluster

# remote PostgreSQL
docker compose --env-file .env -f compose.remote.yml up -d --build pg-1 pg-2

# local PostgreSQL
docker compose --env-file .env -f compose.local.yml up -d --build pg-3
```

Затем проверьте `patronictl list` и отдельно запустите `postgres/service`.
