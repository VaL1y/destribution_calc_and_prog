# Tier 4 — PostgreSQL + Patroni + ZooKeeper

Patroni управляет ролями PostgreSQL и автоматическим failover. ZooKeeper служит
DCS: хранит состояние Patroni и лидерскую блокировку. Складские данные остаются
в PostgreSQL и передаются между узлами обычной WAL-репликацией.

Размещение стенда:

```text
DC-1 (remote)              DC-2 (local)       независимый witness
pg-1 + Patroni             pg-3 + Patroni     ZooKeeper-3
pg-2 + Patroni             ZooKeeper-2
ZooKeeper-1
```

Каждая площадка имеет ровно один голос ZooKeeper. Поэтому потеря любого одного
места оставляет два из трёх голосов, а ни одна изолированная площадка не может
сама образовать большинство.

Скопируйте `.env.example` в `.env` на всех трёх машинах и задайте доступные между
ними адреса, предпочтительно из отдельной WireGuard/LAN-сети.

Сначала запустите по одному ZooKeeper на каждой площадке:

```bash
# DC-1
docker compose -f compose.remote.yml up -d zk-1

# DC-2
docker compose -f compose.local.yml up -d zk-2

# witness
docker compose -f compose.witness.yml up -d zk-3
```

После формирования quorum запустите PostgreSQL/Patroni:

```bash
# DC-1
docker compose -f compose.remote.yml up -d --build pg-1 pg-2

# DC-2
docker compose -f compose.local.yml up -d --build pg-3
```

Состояние Patroni:

```bash
docker compose -f compose.remote.yml exec pg-1 patronictl -c /etc/patroni/patroni.yml list
```

Приложение разворачивается отдельно из `../service`. При подключении через
опубликованные адреса задаются два адреса DC-1 и один адрес DC-2:

```env
DB_WRITE_HOSTS=DC1_IP,DC1_IP,DC2_IP
DB_READ_HOSTS=DC2_IP,DC1_IP,DC1_IP
DB_PORTS=5433,5434,5432
```

ZooKeeper-3 не хранит PostgreSQL и не обслуживает приложение. Он является
третьим независимым голосом. Открывайте PostgreSQL, Patroni REST и ZooKeeper
только между доверенными адресами/VPN; учебный стенд не включает TLS и firewall.
