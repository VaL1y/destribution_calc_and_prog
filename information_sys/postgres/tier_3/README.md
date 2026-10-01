# Tier 3 — PostgreSQL + repmgr

Три PostgreSQL-узла используют `repmgr`: он регистрирует topology, следит за
primary и может повысить standby. Это удобнее ручного `pg_ctl promote`, но у
стенда нет независимого quorum/DCS, поэтому сетевое разделение способно создать
два writable primary (split brain).

## Из чего складывается конфигурация

Общий блок `x-postgres-common` — это YAML anchor Compose: он не относится ни к
PostgreSQL, ни к repmgr, а только устраняет повторение одинаковых параметров.

Параметры образа можно разделить на три группы:

- `POSTGRESQL_DATABASE`, `POSTGRESQL_USERNAME`, `POSTGRESQL_PASSWORD` — база и
  пользователь приложения; `POSTGRESQL_POSTGRES_PASSWORD` — пароль администратора.
- `REPMGR_PASSWORD`, `REPMGR_PRIMARY_HOST`, `REPMGR_PARTNER_NODES` — пароль
  служебного пользователя, начальный primary и полный список участников.
- `REPMGR_NODE_ID`, `REPMGR_NODE_NAME`, `REPMGR_NODE_NETWORK_NAME` — уникальная
  идентичность каждой ноды. Имя из `REPMGR_NODE_NETWORK_NAME` должно разрешаться
  остальными контейнерами.

Остальные сохранённые параметры нужны именно выбранному сценарию, но не являются
минимальным требованием repmgr:

- `REPMGR_NODE_PRIORITY` делает результат выборов предсказуемым: сначала `pg-1`,
  затем `pg-2`, затем `pg-3`.
- `REPMGR_USE_PGREWIND=yes` позволяет вернуть старый primary как standby без
  полного копирования, когда rewind возможен.
- `POSTGRESQL_INITDB_ARGS=--data-checksums` создаёт кластер с checksums, которые
  необходимы `pg_rewind`, если не включён `wal_log_hints`.

`healthcheck`, `restart`, `ports` и `volumes` относятся к эксплуатации Docker:
они не создают репликацию. Volume сохраняет данные, healthcheck показывает
готовность, restart перезапускает процесс, а ports открывает доступ с хоста.

## База

```cmd
docker compose up -d
docker compose exec pg-1 repmgr -f /opt/bitnami/repmgr/conf/repmgr.conf cluster show
```

## Приложение отдельно

Сначала выполните миграции и запустите удалённую ветку:

```cmd
cd ../service
docker compose up -d --build api
docker network connect warehouse-tier3-net warehouse-postgres-service-api-1
docker compose exec api python scripts/migrate.py
```

Для отдельного приложения локальной ветки используйте второй Compose project,
порт и сеть. Оба приложения получают одинаковый список узлов; доступность
конкретных узлов определяется тем, к каким сетям подключён контейнер:

```cmd
set "API_PORT=8001"
set "APP_NODE=local"
docker compose -p warehouse-local up -d --build api
docker network connect warehouse-tier3-local-branch warehouse-local-api-1
docker network connect warehouse-tier3-net warehouse-local-api-1
```

При обычной работе подключите второй API также к `warehouse-tier3-net`. Для
разделения отключите от неё одновременно `pg-3` и второй API, оставив их в
`warehouse-tier3-local-branch`; после восстановления подключите оба обратно.

Пошаговые эксперименты сохранены в `docs/`. После учебного split brain применяется
политика winner-takes-all: действующий primary с актуальной timeline сохраняется,
а проигравшая нода при перезапуске перематывается через `pg_rewind` (либо заново
клонируется образом, если rewind невозможен) и возвращается как standby. Для
новых volume включены data checksums, необходимые `pg_rewind`.
