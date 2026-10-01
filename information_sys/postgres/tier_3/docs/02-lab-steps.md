# Базовый эксперимент tier_3

```cmd
docker compose up -d
docker compose exec pg-1 repmgr -f /opt/bitnami/repmgr/conf/repmgr.conf cluster show
```

Создайте схему независимым сервисом:

```cmd
cd ../service
docker compose up -d --build api
docker network connect warehouse-tier3-net warehouse-postgres-service-api-1
docker compose exec api python scripts/migrate.py
```

Проверки:

```cmd
curl http://127.0.0.1:8000/api/demo/node
curl http://127.0.0.1:8000/api/products
```

Остановите standby, сделайте запись, верните standby и наблюдайте, как он
догоняет WAL. Затем остановите текущий primary и замерьте время до нового leader
в `repmgr cluster show` и время восстановления записи через API.
