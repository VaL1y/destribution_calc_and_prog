# Дополнительный вариант — Patroni + etcd

Стенд повторяет `tier_4`, но использует etcd вместо ZooKeeper. PostgreSQL и
Patroni работают одинаково; меняется реализация DCS и её операционные команды.

```bash
# remote
docker compose --env-file .env -f compose.remote.yml up -d --build

# local
docker compose --env-file .env -f compose.local.yml up -d --build
```

Проверка quorum etcd:

```bash
docker compose -f compose.remote.yml exec etcd-1 \
  etcdctl endpoint status --cluster -w table
```

Приложение находится в `../../service` и подключается по опубликованным портам.
Как и в ZooKeeper-варианте, размещение 2+1 безопасно при сетевом разделении, но
не обеспечивает автоматический failover после полной потери стороны с двумя
голосами.
