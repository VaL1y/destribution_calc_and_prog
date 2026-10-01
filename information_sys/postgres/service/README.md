# Warehouse service

Один и тот же FastAPI-сервис используется со всеми PostgreSQL-стендами. Он не
запускает и не настраивает PostgreSQL: адреса узлов и режим чтения передаются
через переменные окружения.

## Запуск с tier_1

```cmd
docker compose up -d --build api
docker compose -f ..\tier_1\compose.yml up -d
docker network create warehouse-lab
docker network connect warehouse-lab warehouse-postgres-service-api-1
docker network connect --alias pg-1 warehouse-lab warehouse-pg-tier1-pg-1-1
docker compose exec api python scripts/migrate.py
```

Интерфейс: <http://127.0.0.1:8000>. Статус: `GET /api/status`.
`GET /api/demo/node` показывает узел записи, а `GET /api/demo/read-node` — узел,
который выбрал read-pool.

Для кластера задаются списки узлов:

```env
DB_WRITE_HOSTS=pg-1,pg-2,pg-3
DB_READ_HOSTS=pg-3,pg-2,pg-1
DB_PORTS=5432
```

`target_session_attrs=read-write` направляет запись на доступный primary.
`prefer-standby` предпочитает standby для чтения, но допускает fallback на
primary. Это маршрутизация клиента, а не механизм выборов нового primary.

Нагрузочный интерфейс запускается командой:

```cmd
docker compose --profile load up -d locust
```

Locust: <http://127.0.0.1:8089>.

`HISTORICAL_LOAD_TEST_REPORT.md` содержит цифры прежнего однонодового запуска;
это baseline, а не результат новых tier_2/tier_4 стендов.
