# Архитектура tier_3

`pg-1`, `pg-2`, `pg-3` — полноценные экземпляры PostgreSQL. WAL идёт от
текущего primary к standby. `repmgr` хранит topology в PostgreSQL, наблюдает за
узлами и вызывает promotion, но не создаёт независимый consensus-кворум.

```text
remote branch: pg-1 <-> pg-2       local branch: pg-3
                    \             /
                     replication
```

Приложение вынесено в `postgres/service`. Для обычной работы оно подключается к
сети `warehouse-tier3-net` и перебирает `pg-1,pg-2,pg-3`. Для split-brain опыта
второй экземпляр приложения подключается только к сети
`warehouse-tier3-local-branch` и узлу `pg-3`.

После promotion старый primary нельзя просто подключить обратно как равного:
timeline разошлись. Его нужно вернуть через `pg_rewind`/reclone. Если запись шла
в обе ветки, PostgreSQL физической репликацией не умеет автоматически сливать
два набора изменений.
