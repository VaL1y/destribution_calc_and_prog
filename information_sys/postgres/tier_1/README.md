# Tier 1 — один PostgreSQL

Один нормально настроенный экземпляр PostgreSQL без репликации. Этот уровень
нужен как базовая точка для CRUD, нагрузки и сравнения задержек.

```powershell
docker network create warehouse-lab
docker compose up -d
docker compose ps
docker compose exec pg-1 psql -U warehouse -d warehouse -c "select pg_is_in_recovery();"
```

Результат `f`: узел является обычным primary. При его остановке база полностью
недоступна. CAP здесь ещё неприменима: распределённой системы нет.

Таблицы создаёт отдельный сервис:

```powershell
cd ../service
docker compose build
docker compose --profile tools run --rm migrate
docker compose up -d api
```

PostgreSQL опубликован только на loopback-порту `15432`; приложение внутри
Docker-сети обращается к нему как `pg-1:5432`.
