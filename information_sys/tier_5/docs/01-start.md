# Пошаговый запуск tier_5

## 1. Сеть и файлы

Используйте постоянные приватные/WireGuard-адреса. Между серверами разрешите:

| Узел | Порты по умолчанию | Назначение |
|---|---|---|
| удалённый | 2181, 2182 | клиенты ZooKeeper |
| удалённый | 2888, 2889 | синхронизация ZooKeeper |
| удалённый | 3888, 3889 | выборы ZooKeeper |
| удалённый | 5433, 5434 | PostgreSQL pg-1 и pg-2 |
| удалённый | 8008, 8009 | Patroni REST API |
| локальный | 2181, 2888, 3888 | ZooKeeper-3 |
| локальный | 5432, 8008 | PostgreSQL и Patroni pg-3 |

На оба сервера перенесите `information_sys/tier_2` и `information_sys/tier_5`.
На обоих создайте одинаковый `.env`:

```bash
cd information_sys/tier_5
cp .env.example .env
```

Замените адреса и все пароли. Затем проверьте нужный для сервера Compose-файл:

```bash
docker compose --env-file .env -f compose.remote.yml config --quiet
docker compose --env-file .env -f compose.local.yml config --quiet
```

## 2. Поднять ансамбль ZooKeeper

На локальном сервере:

```bash
docker compose --env-file .env -f compose.local.yml up -d zk-3
```

На удалённом сервере:

```bash
docker compose --env-file .env -f compose.remote.yml up -d zk-1 zk-2
```

Проверьте логи всех трёх. Участники должны выбрать один `leader`, двое станут
`follower`. На удалённом сервере:

```bash
docker compose --env-file .env -f compose.remote.yml exec zk-1 zkServer.sh status
docker compose --env-file .env -f compose.remote.yml exec zk-2 zkServer.sh status
```

На локальном сервере:

```bash
docker compose --env-file .env -f compose.local.yml exec zk-3 zkServer.sh status
```

## 3. Bootstrap PostgreSQL

Сначала создайте определённый первый primary на удалённом сервере:

```bash
docker compose --env-file .env -f compose.remote.yml up -d --build pg-1
docker compose --env-file .env -f compose.remote.yml logs -f pg-1
```

После успешного bootstrap добавьте остальные компоненты.

На удалённом сервере:

```bash
docker compose --env-file .env -f compose.remote.yml up -d --build pg-2 api
```

На локальном сервере:

```bash
docker compose --env-file .env -f compose.local.yml up -d --build pg-3
```

## 4. Проверка

```bash
docker compose --env-file .env -f compose.remote.yml exec pg-1 \
  patronictl -c /etc/patroni/patroni.yml list
```

Должен быть один `Leader` и две `Replica`. Откройте
`http://REMOTE_HOST:8000`, выполните приход и обновите список. Запись ищет primary,
чтение предпочитает standby.

Конфигурация PostgreSQL/Patroni совпадает с `tier_4`. Поэтому различия поведения
в опытах относятся прежде всего к эксплуатации и диагностике DCS, а не к иной
модели репликации данных.

