# PostgreSQL labs

| Каталог | Что изучаем | Кто выбирает primary |
|---|---|---|
| `tier_1` | одна нода и базовая нагрузка | выбора нет |
| `tier_2` | streaming replication: async/sync | оператор вручную |
| `tier_3` | автоматизация через repmgr, split brain | repmgr без независимого DCS |
| `tier_4` | Patroni + ZooKeeper, quorum | Patroni через лидерский lock в DCS |
| `extra/patroni-etcd` | тот же Patroni с etcd для сравнения DCS | Patroni через etcd |

`service` — независимое FastAPI-приложение и миграции. Каждый уровень БД можно
запустить, проверить через `psql`, а затем подключить тот же сервис.

## Правильный порядок

1. Создать требуемую сеть или межсерверный VPN.
2. Поднять выбранный уровень PostgreSQL.
3. Выполнить `service`-миграции на текущем writable primary.
4. Запустить FastAPI и нагрузку.
5. Провести отказ и записать RTO, RPO, ошибки клиента и состояние реплик.

CAP применяется только когда появляется распределение и возможен network
partition. Один PostgreSQL — не «CA-система», потому что у него ещё нет выбора
между consistency и availability во время разделения сети.
