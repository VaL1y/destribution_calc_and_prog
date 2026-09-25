# Tier 3 — PostgreSQL + repmgr

Три PostgreSQL-узла используют `repmgr`: он регистрирует topology, следит за
primary и может повысить standby. Это удобнее ручного `pg_ctl promote`, но у
стенда нет независимого quorum/DCS, поэтому сетевое разделение способно создать
два writable primary (split brain).

## База

```powershell
docker compose up -d
docker compose exec pg-1 repmgr -f /opt/bitnami/repmgr/conf/repmgr.conf cluster show
```

## Приложение отдельно

Сначала выполните миграции и запустите удалённую ветку:

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

Для отдельного приложения локальной ветки используйте второй Compose project,
порт и сеть:

```powershell
$env:DB_NETWORK='warehouse-tier3-local-branch'
$env:DB_WRITE_HOSTS='pg-3'
$env:DB_READ_HOSTS='pg-3'
$env:API_PORT='8001'
$env:APP_NODE='local'
docker compose -p warehouse-local up -d api
```

Пошаговые эксперименты сохранены в `docs/`. Согласование событий после учебного
split brain выполняет `service/scripts/reconcile_events.py`; это прикладное
слияние append-only событий, не автоматическое слияние PostgreSQL-кластеров.
