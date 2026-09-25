# Tier 2 — чистый PostgreSQL primary + standby

Здесь нет менеджера отказоустойчивости. PostgreSQL передаёт WAL на standby,
но сам не решает, кого повышать до primary и куда должно подключаться приложение.

Одновременно запускайте только один режим — у вариантов одинаковые DNS-имена.

## Асинхронный режим

```powershell
docker network create warehouse-lab
docker compose -f compose.async.yml up -d --build
docker compose -f compose.async.yml exec pg-primary psql -U warehouse -d warehouse -c "select application_name,state,sync_state from pg_stat_replication;"
```

Для сервиса используйте:

```env
DB_WRITE_HOSTS=pg-primary
DB_READ_HOSTS=pg-standby,pg-primary
DB_PORTS=5432
```

Если остановить standby, primary продолжит подтверждать запись. Это высокая
доступность записи на стороне primary, но последние WAL могут быть потеряны при
его последующем отказе.

## Синхронный режим

```powershell
docker compose -f compose.sync.yml up -d --build
```

`synchronous_commit=remote_apply` подтверждает COMMIT только после применения
транзакции standby. При остановленном standby сам primary остаётся доступен:
SELECT работает, соединения создаются, но COMMIT ожидает синхронный узел.
Откройте отдельную psql-сессию, выполните INSERT и наблюдайте `wait_event=SyncRep`
из второй сессии. Завершайте учебный клиент внешним timeout/`Ctrl+C`.

Важный нюанс: разрыв клиентского ожидания не доказывает rollback. PostgreSQL мог
уже локально зафиксировать транзакцию и ждать лишь подтверждение standby. После
возврата реплики строка может появиться — тот же класс неопределённого результата,
который в HTTP выглядит как «сначала ошибка, затем данные обновились».

## Проверка ролей

```powershell
docker compose -f compose.async.yml exec pg-primary psql -U warehouse -d warehouse -c "select pg_is_in_recovery();"
docker compose -f compose.async.yml exec pg-standby psql -U warehouse -d warehouse -c "select pg_is_in_recovery();"
```

Ожидаются `f` на primary и `t` на standby. Автоматического failover здесь нет.
