# Пошаговый запуск tier_4

## 1. Подготовить связь

Оба физических сервера должны обращаться друг к другу по постоянным адресам.
Лучше использовать приватную сеть или WireGuard. Не публикуйте PostgreSQL, etcd
и Patroni REST API в интернет.

Разрешите между серверами TCP-порты:

| Узел | Порты по умолчанию | Назначение |
|---|---|---|
| удалённый | 2379, 2381 | клиенты etcd |
| удалённый | 2380, 2382 | обмен членов etcd |
| удалённый | 5433, 5434 | PostgreSQL pg-1 и pg-2 |
| удалённый | 8008, 8009 | Patroni REST API |
| локальный | 2379, 2380 | клиент и peer etcd-3 |
| локальный | 5432 | PostgreSQL pg-3 |
| локальный | 8008 | Patroni REST API pg-3 |

Порт FastAPI 8000 открывайте только тем клиентам, которым нужен склад.

## 2. Перенести файлы

На оба сервера нужны каталоги `information_sys/tier_2` и
`information_sys/tier_4` с сохранением этой структуры. `tier_2` содержит
приложение и исходную схему склада; `tier_4` добавляет HA-конфигурацию.

На каждом сервере:

```bash
cd information_sys/tier_4
cp .env.example .env
```

Заполните один и тот же `.env` на обоих серверах. `REMOTE_HOST` и `LOCAL_HOST`
должны быть реальными доступными адресами, пароли замените. После первого
bootstrap не меняйте кластерные пароли только в `.env`: роли уже записаны в БД.

Проверьте Compose без запуска:

```bash
docker compose --env-file .env -f compose.remote.yml config --quiet
docker compose --env-file .env -f compose.local.yml config --quiet
```

Первая команда предназначена для удалённого сервера, вторая — для локального.

## 3. Поднять три голоса etcd

На локальном сервере:

```bash
docker compose --env-file .env -f compose.local.yml up -d etcd-3
```

На удалённом сервере:

```bash
docker compose --env-file .env -f compose.remote.yml up -d etcd-1 etcd-2
```

Первые два доступных голоса уже образуют кворум. Проверьте с удалённого сервера,
подставив адреса из `.env`:

```bash
docker compose --env-file .env -f compose.remote.yml exec etcd-1 \
  etcdctl --endpoints=http://10.30.0.11:2379,http://10.30.0.11:2381,http://10.30.0.21:2379 \
  endpoint status --cluster -w table
```

Должны быть видны три member и один лидер etcd. Если нет — пока не запускайте
PostgreSQL; проверьте адреса, firewall и логи `docker compose ... logs`.

## 4. Создать первый primary

На удалённом сервере:

```bash
docker compose --env-file .env -f compose.remote.yml up -d --build pg-1
docker compose --env-file .env -f compose.remote.yml logs -f pg-1
```

Первый Patroni получает лидерский ключ, выполняет `initdb`, создаёт роли,
базу и схему склада. Завершите просмотр логов через `Ctrl+C`; контейнер останется
работать.

## 5. Добавить реплики и API

На удалённом сервере:

```bash
docker compose --env-file .env -f compose.remote.yml up -d --build pg-2 api
```

На локальном сервере:

```bash
docker compose --env-file .env -f compose.local.yml up -d --build pg-3
```

Обе новые PostgreSQL-ноды получат base backup с primary и начнут принимать WAL.

## 6. Проверить роли

На удалённом сервере:

```bash
docker compose --env-file .env -f compose.remote.yml exec pg-1 \
  patronictl -c /etc/patroni/patroni.yml list
```

Ожидается один `Leader` и две `Replica`. Затем откройте
`http://REMOTE_HOST:8000`. Приход товара должен записываться на Leader, списки
могут читаться с Replica.

Настройки `ttl=20`, `loop_wait=5`, `retry_timeout=5` дают переключение порядка
десятков секунд, а не мгновенное. Точное время измеряется в следующем документе.

