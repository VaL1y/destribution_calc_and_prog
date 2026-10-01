# Tier 1 — один PostgreSQL

Один нормально настроенный экземпляр PostgreSQL без репликации. Этот уровень
нужен как базовая точка для CRUD, нагрузки и сравнения задержек.

```cmd
docker compose up -d
docker compose ps
docker compose exec pg-1 psql -U warehouse -d warehouse -c "select pg_is_in_recovery();"
```

Результат `f`: узел является обычным primary. При его остановке база полностью
недоступна. CAP здесь ещё неприменима: распределённой системы нет.

Таблицы создаёт отдельный сервис:

```cmd
cd ../service
docker compose up -d --build api
docker network create warehouse-lab
docker network connect warehouse-lab warehouse-postgres-service-api-1
docker network connect --alias pg-1 warehouse-lab warehouse-pg-tier1-pg-1-1
docker compose exec api python scripts/migrate.py
```

PostgreSQL опубликован только на loopback-порту `15432`; приложение внутри
Docker-сети обращается к нему как `pg-1:5432`.
