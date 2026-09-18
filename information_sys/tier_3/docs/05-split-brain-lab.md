# Лабораторная работа: split-brain и согласование событий

Этот опыт выполняется только после штатного failover и возврата всех трёх нод.
Перед началом `repmgr cluster show` должен показывать одну primary и две standby.

В Compose есть две сети:

- `warehouse-tier3-net` связывает удалённую ветку `pg-1`, `pg-2` и `pg-3` для
  обычной WAL-репликации;
- `warehouse-tier3-local-branch` связывает только `api-local` и `pg-3`.

Мы отключим `pg-3` только от первой сети. Она потеряет primary, но останется
доступной локальному приложению. Удалённая primary продолжит работу отдельно.

## 1. Применить новую сеть и запустить локальное приложение

```bash
docker compose --profile splitbrain up -d api-local
docker compose ps
```

Пока `pg-3` является standby, запись через локальную ветку запрещена:

```bash
curl -i -X POST http://127.0.0.1:8001/api/demo/events \
  -H 'Content-Type: application/json' \
  -d '{"product_id":1,"delta":1,"note":"До разделения: запись должна быть запрещена"}'
```

Ожидается HTTP 503.

## 2. Создать общее событие до разделения

```bash
curl -sS -X POST http://127.0.0.1:8000/api/demo/events \
  -H 'Content-Type: application/json' \
  -d '{"product_id":1,"delta":10,"note":"Общее событие до разделения"}'
```

Убедитесь, что событие дошло до `pg-3`, и сохраните его UUID.

## 3. Разделить сеть

Узнать точное имя контейнера:

```bash
docker compose ps pg-3
```

При стандартном имени проекта отключение выполняется так:

```bash
docker network disconnect warehouse-tier3-net warehouse-ha-lab-pg-3-1
```

Не останавливайте контейнер. `pg-3` остаётся в сети
`warehouse-tier3-local-branch`, но больше не видит `pg-1` и `pg-2`.

Следить за решением `repmgrd`:

```bash
docker compose logs -f --since=1m pg-3
```

После promotion проверить через локальное приложение:

```bash
curl -sS http://127.0.0.1:8001/api/demo/node
```

`in_recovery` должно стать `false`. Удалённое приложение на порту 8000 также
должно видеть writable primary. Это и есть две одновременно writable ветки.

## 4. Сделать независимые записи

Удалённая ветка:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/demo/events \
  -H 'Content-Type: application/json' \
  -d '{"product_id":1,"delta":20,"note":"Событие удалённой ветки"}'
```

Локальная ветка:

```bash
curl -sS -X POST http://127.0.0.1:8001/api/demo/events \
  -H 'Content-Type: application/json' \
  -d '{"product_id":1,"delta":30,"note":"Событие локальной ветки"}'
```

Сохраните оба UUID. На каждой ветке теперь есть общее событие и только одно из
двух новых событий.

## 5. Зафиксировать данные перед восстановлением сети

Остановить оба приложения, чтобы набор данных больше не менялся:

```bash
docker compose stop api-remote api-local
```

Выгрузить локальные события в файл внутри volume не требуется: `pg-3` пока
остаётся работающей самостоятельной primary. Сначала подключаем её к общей сети,
но не возвращаем в streaming replication.

```bash
docker network connect warehouse-tier3-net warehouse-ha-lab-pg-3-1
```

На этом этапе две primary снова видят друг друга. Приложения остановлены, поэтому
новых пользовательских записей нет. Не перезапускайте `pg-3` и не выполняйте
rejoin до копирования уникальных событий.

## 6. Пробное согласование append-only событий

Узнать текущую primary удалённой ветки через `repmgr cluster show`. В примерах
ниже это `pg-2`; если у вас primary другая, замените target.

```bash
docker compose run --rm --no-deps api-remote \
  python tier3_scripts/reconcile_events.py \
  --source-host pg-3 --target-host pg-2 --dry-run
```

Скрипт сравнивает UUID и показывает события, которых нет в выбранной итоговой
primary. Он не изменяет произвольные таблицы склада.

Если dry-run показывает локальное событие, выполнить перенос:

```bash
docker compose run --rm --no-deps api-remote \
  python tier3_scripts/reconcile_events.py \
  --source-host pg-3 --target-host pg-2
```

Проверить, что на итоговой primary присутствуют все три события: общее,
удалённое и локальное.

## 7. Вернуть `pg-3` как standby

Теперь локальная ветка уже сохранена в итоговой primary. Перезапуск `pg-3`
позволяет Bitnami entrypoint обнаружить действующую primary и пересоздать
расходящуюся ноду как standby:

```bash
docker compose restart pg-3
docker compose logs -f --since=1m pg-3
```

После завершения проверить роли и только затем вернуть приложение:

```bash
docker compose start api-remote
docker compose exec pg-2 \
  /opt/bitnami/scripts/postgresql-repmgr/entrypoint.sh \
  repmgr -f /opt/bitnami/repmgr/conf/repmgr.conf cluster show
```

`api-local` можно оставить остановленным до следующего эксперимента.

## Что демонстрирует опыт

repmgr без независимого кворума не может надёжно отличить падение primary от
разрыва сети. Поэтому изолированная `pg-3` повышается, пока старая primary всё
ещё принимает записи. Произвольное автоматическое слияние PostgreSQL timeline
невозможно. Мы сохранили обе ветки только потому, что заранее выбрали простую
append-only модель с глобальными UUID и `ON CONFLICT DO NOTHING`.
