# Пошаговый запуск ZooKeeper-стенда

1. Настройте взаимную доступность `REMOTE_HOST`, `LOCAL_HOST` и `WITNESS_HOST`.
2. Скопируйте одинаковый `.env` на все три машины.
3. Проверьте соответствующий Compose на каждой площадке:

```bash
# DC-1
docker compose --env-file .env -f compose.remote.yml config --quiet

# DC-2
docker compose --env-file .env -f compose.local.yml config --quiet

# witness
docker compose --env-file .env -f compose.witness.yml config --quiet
```

4. Запустите три ZooKeeper-ноды — по одной на площадку:

```bash
# DC-1
docker compose --env-file .env -f compose.remote.yml up -d zk-1

# DC-2
docker compose --env-file .env -f compose.local.yml up -d zk-2

# witness
docker compose --env-file .env -f compose.witness.yml up -d zk-3
```

5. После формирования ZooKeeper quorum запустите PostgreSQL/Patroni:

```bash
# DC-1
docker compose --env-file .env -f compose.remote.yml up -d --build pg-1 pg-2

# DC-2
docker compose --env-file .env -f compose.local.yml up -d --build pg-3
```

6. Проверьте, что существует ровно один leader:

```bash
docker compose --env-file .env -f compose.remote.yml exec pg-1 \
  patronictl -c /etc/patroni/patroni.yml list
```

7. Подключите независимое приложение из `postgres/service` и выполните миграцию.
FastAPI не входит в Compose-файлы Tier 4.
