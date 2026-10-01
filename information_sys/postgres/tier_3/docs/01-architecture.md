# Архитектура tier_3

`pg-1`, `pg-2`, `pg-3` — полноценные экземпляры PostgreSQL. WAL идёт от
текущего primary к standby. `repmgr` хранит topology в PostgreSQL, наблюдает за
узлами и вызывает promotion, но не создаёт независимый consensus-кворум.

```text
remote branch: pg-1 <-> pg-2       local branch: pg-3
                    \             /
                     replication
```

Приложение вынесено в `postgres/service`. Оба его экземпляра получают полный
список `pg-1,pg-2,pg-3`. Для split-brain опыта второй API и `pg-3` одновременно
отключаются от `warehouse-tier3-net`, но остаются вместе в
`warehouse-tier3-local-branch`; недоступные адреса драйвер пропускает.

После promotion старый primary нельзя просто подключить обратно как равного:
timeline разошлись. При перезапуске проигравшей ноды образ пытается вернуть её к
действующему primary через `pg_rewind`, а при невозможности выполняет reclone.
Изменения проигравшей ветки теряются: PostgreSQL физической репликацией не умеет
объединять два набора изменений.
