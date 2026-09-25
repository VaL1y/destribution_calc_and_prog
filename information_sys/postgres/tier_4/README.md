# Tier 4 — PostgreSQL + Patroni + ZooKeeper

Patroni управляет ролями PostgreSQL и failover. ZooKeeper является DCS:
хранит лидерский lock и состояние кластера. Сами складские данные остаются в
PostgreSQL и передаются обычной WAL-репликацией.

Размещение стенда:

```text
удалённый сервер                 локальный сервер
pg-1 + Patroni                   pg-3 + Patroni
pg-2 + Patroni                   ZooKeeper-3
ZooKeeper-1, ZooKeeper-2
```

Скопируйте `.env.example` в `.env` на обе машины и укажите доступные друг другу
IP (предпочтительно адреса WireGuard). На удалённой машине:

```bash
docker compose -f compose.remote.yml up -d --build
```

На локальном сервере:

```bash
docker compose -f compose.local.yml up -d --build
```

Состояние Patroni:

```bash
docker compose -f compose.remote.yml exec pg-1 patronictl -c /etc/patroni/patroni.yml list
```

Приложение разворачивается отдельно из `../service`. Для подключения вне
Docker-сети задайте реальные IP и соответствующие порты:

```env
DB_WRITE_HOSTS=REMOTE_IP,REMOTE_IP,LOCAL_IP
DB_READ_HOSTS=REMOTE_IP,REMOTE_IP,LOCAL_IP
DB_PORTS=5433,5434,5432
```

Важно: два из трёх голосов ZooKeeper находятся на удалённом физическом сервере.
Это предотвращает split brain при разрыве связи, но потеря всего удалённого
сервера лишает локальную сторону quorum. Чтобы автоматически переживать отказ
любого ЦОД, третий голос нужно разместить в третьем независимом месте. Два
физических места не позволяют безопасно отличить сетевой разрыв от полного
отказа второй стороны.

Открывайте порты только между доверенными адресами/VPN. REST API Patroni и
ZooKeeper в этом учебном стенде не защищены TLS.
