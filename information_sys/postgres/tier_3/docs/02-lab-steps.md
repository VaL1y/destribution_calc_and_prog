# Базовый эксперимент tier_3

```powershell
docker compose up -d
docker compose exec pg-1 repmgr -f /opt/bitnami/repmgr/conf/repmgr.conf cluster show
```

Создайте схему независимым сервисом:

```powershell
cd ../service
$env:DB_NETWORK='warehouse-tier3-net'
$env:DB_WRITE_HOSTS='pg-1,pg-2,pg-3'
$env:DB_READ_HOSTS='pg-2,pg-3,pg-1'
$env:DB_PORTS='5432'
docker compose build
docker compose --profile tools run --rm migrate
docker compose up -d api
```

Проверки:

```powershell
curl http://127.0.0.1:8000/api/demo/node
curl http://127.0.0.1:8000/api/products
```

Остановите standby, сделайте запись, верните standby и наблюдайте, как он
догоняет WAL. Затем остановите текущий primary и замерьте время до нового leader
в `repmgr cluster show` и время восстановления записи через API.
