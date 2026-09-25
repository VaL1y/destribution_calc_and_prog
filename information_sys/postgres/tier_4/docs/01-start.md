# Пошаговый запуск ZooKeeper-стенда

1. Настройте WireGuard/LAN и проверьте взаимную доступность `REMOTE_HOST` и
   `LOCAL_HOST`.
2. Скопируйте одинаковый `.env` на оба сервера.
3. Проверьте Compose на каждой машине:

```bash
docker compose --env-file .env -f compose.remote.yml config --quiet
docker compose --env-file .env -f compose.local.yml config --quiet
```

4. Сначала запустите ZooKeeper-3 локально, затем ZooKeeper-1/2 удалённо:

```bash
# local
docker compose --env-file .env -f compose.local.yml up -d zk-3

# remote
docker compose --env-file .env -f compose.remote.yml up -d zk-1 zk-2
docker compose --env-file .env -f compose.remote.yml exec zk-1 zkServer.sh status
```

5. Запустите PostgreSQL/Patroni:

```bash
# remote
docker compose --env-file .env -f compose.remote.yml up -d --build pg-1 pg-2

# local
docker compose --env-file .env -f compose.local.yml up -d --build pg-3
```

6. Проверьте роли:

```bash
docker compose --env-file .env -f compose.remote.yml exec pg-1 \
  patronictl -c /etc/patroni/patroni.yml list
```

7. Из `postgres/service` подключите приложение к трём опубликованным адресам и
   выполните миграции. FastAPI не входит в эти Compose-файлы.
