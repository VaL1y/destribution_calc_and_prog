# Warehouse service

Один и тот же FastAPI-сервис используется со всеми PostgreSQL-стендами. Он не
запускает и не настраивает PostgreSQL: адреса узлов и режим чтения передаются
через переменные окружения.

## Запуск с tier_1

```powershell
docker network create warehouse-lab
docker compose -f ../tier_1/compose.yml up -d
docker compose build
docker compose --profile tools run --rm migrate
docker compose up -d api
```

Интерфейс: <http://127.0.0.1:8000>. Статус: `GET /api/status`.
`GET /api/demo/node` показывает узел записи, а `GET /api/demo/read-node` — узел,
который выбрал read-pool.

Для кластера задаются списки узлов:

```env
DB_WRITE_HOSTS=pg-1,pg-2,pg-3
DB_READ_HOSTS=pg-2,pg-3,pg-1
DB_PORTS=5432
```

`target_session_attrs=read-write` направляет запись на доступный primary.
`prefer-standby` предпочитает standby для чтения, но допускает fallback на
primary. Это маршрутизация клиента, а не механизм выборов нового primary.

Нагрузочный интерфейс запускается командой:

```powershell
docker compose --profile load up -d locust
```

Locust: <http://127.0.0.1:8089>.

`HISTORICAL_LOAD_TEST_REPORT.md` содержит цифры прежнего однонодового запуска;
это baseline, а не результат новых tier_2/tier_4 стендов.
