# Пошаговый локальный запуск

Команды выполняются из `information_sys/tier_3`. Сам стенд при подготовке этих
файлов не запускался.

## Шаг 0. Проверить конфигурацию без запуска

```powershell
Copy-Item .env.example .env
docker compose config
```

Перед продолжением замените три пароля в `.env`. Команда `config` только
разворачивает YAML anchors и переменные; контейнеры она не создаёт.

## Шаг 1. Поднять initial primary

```powershell
docker compose up -d pg-1
docker compose logs -f pg-1
```

При первом старте контейнер:

1. выполняет `initdb`;
2. создаёт пользователей `warehouse` и `repmgr`;
3. выполняет SQL из `tier_2/postgres/init`;
4. регистрирует `pg-1` как initial primary;
5. запускает PostgreSQL и `repmgrd`.

Остановите просмотр логов через `Ctrl+C`, затем проверьте:

```powershell
docker compose exec pg-1 psql -U warehouse -d warehouse -c "select pg_is_in_recovery();"
docker compose exec pg-1 repmgr -f /opt/bitnami/repmgr/conf/repmgr.conf cluster show
```

На primary `pg_is_in_recovery()` возвращает `false`.

## Шаг 2. Добавить первую standby

```powershell
docker compose up -d pg-2
docker compose logs -f pg-2
```

При пустом volume `pg-2` получает base backup от `pg-1`, запускается в recovery
и регистрируется как standby.

```powershell
docker compose exec pg-2 psql -U warehouse -d warehouse -c "select pg_is_in_recovery();"
docker compose exec pg-1 repmgr -f /opt/bitnami/repmgr/conf/repmgr.conf cluster show
```

На standby запрос возвращает `true`.

## Шаг 3. Добавить вторую standby

```powershell
docker compose up -d pg-3
docker compose logs -f pg-3
docker compose exec pg-1 repmgr -f /opt/bitnami/repmgr/conf/repmgr.conf cluster show
```

Ожидаем одну строку `primary` и две строки `standby`.

## Шаг 4. Увидеть физическую репликацию

На primary:

```powershell
docker compose exec pg-1 psql -U postgres -d warehouse -c "select application_name, state, sent_lsn, write_lsn, flush_lsn, replay_lsn from pg_stat_replication order by application_name;"
```

На каждой standby:

```powershell
docker compose exec pg-2 psql -U postgres -d warehouse -c "select status, received_lsn, latest_end_lsn from pg_stat_wal_receiver;"
docker compose exec pg-3 psql -U postgres -d warehouse -c "select status, received_lsn, latest_end_lsn from pg_stat_wal_receiver;"
```

## Шаг 5. Поднять FastAPI

```powershell
docker compose up -d --build api-remote
docker compose logs -f api-remote
```

Интерфейс: `http://localhost:8000`.

Проверить, куда попадают подключения API:

```powershell
docker compose exec pg-1 psql -U postgres -d warehouse -c "select application_name, client_addr, state from pg_stat_activity where usename = 'warehouse';"
docker compose exec pg-2 psql -U postgres -d warehouse -c "select application_name, client_addr, state from pg_stat_activity where usename = 'warehouse';"
docker compose exec pg-3 psql -U postgres -d warehouse -c "select application_name, client_addr, state from pg_stat_activity where usename = 'warehouse';"
```

Swagger с демонстрационными endpoint: `http://localhost:8000/docs`.

До split-brain можно создать общее событие прихода через
`POST /api/demo/events`; оно должно реплицироваться на обе standby.

## Шаг 6. Только после проверки — Locust

```powershell
docker compose --profile load up -d locust
```

Интерфейс Locust: `http://localhost:8089`.

## Шаг 7. Подготовить второе приложение

```powershell
docker compose --profile splitbrain up -d api-local
```

Swagger локальной ветки: `http://localhost:8001/docs`.

Пока `pg-3` является standby, `POST /api/demo/events` на порту `8001` должен
вернуть `503`. После изоляции и promotion `pg-3` тот же запрос станет успешным.

## Сценарий согласования после split-brain

Точные команды сетевой изоляции и promotion добавим после первого запуска —
они зависят от фактического поведения repmgr в выбранном образе. Логика опыта
уже зафиксирована:

1. Создать общее событие до разделения.
2. Разделить удалённую и локальную ветки.
3. Добиться появления двух writable primary.
4. Через порт `8000` создать событие с `source_node=remote`.
5. Через порт `8001` создать событие с `source_node=local`.
6. Остановить оба API, чтобы зафиксировать набор данных.
7. Восстановить сеть и выбрать итоговый primary.
8. Сначала выполнить пробный перенос:

```powershell
docker compose run --rm api-remote python tier3_scripts/reconcile_events.py --source-host pg-3 --target-host pg-1 --dry-run
```

9. Повторить без `--dry-run`:

```powershell
docker compose run --rm api-remote python tier3_scripts/reconcile_events.py --source-host pg-3 --target-host pg-1
```

10. Проверить, что итоговый primary содержит общее, remote и local события.
11. Только после этого вернуть проигравшую ноду через rewind/reinitialize.

Если итоговым выбран `pg-3`, параметры source и target меняются местами.

## Следующие лабораторные опыты

Они намеренно не автоматизированы одним скриптом.

1. Остановить `pg-2`, выполнять записи, запустить её и измерить catch-up.
2. Остановить текущий primary и измерить время до promotion.
3. Остановить одновременно `pg-1` и `pg-2`; проверить promotion `pg-3`.
4. Разорвать Docker-сеть только для `pg-3`, создать две независимые записи и
   объединить UUID-события.
5. После согласования вернуть старый primary и увидеть, почему одной перезагрузки
   недостаточно при расходящихся timeline.
6. Сразу после записи читать с standby и наблюдать read-after-write lag.

Команды и критерии успеха для каждого опыта добавим после того, как базовый
кластер впервые будет поднят и его фактическое поведение будет зафиксировано.

## Удаление стенда

Обычная остановка сохраняет данные:

```powershell
docker compose stop
```

Команда `docker compose down -v` удалит все три базы. Не выполняйте её, пока
данные нужны для последующих опытов.
