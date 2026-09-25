# Split-brain и учебное согласование событий

1. Поднимите кластер и выполните миграции по `02-lab-steps.md`.
2. Запустите второй экземпляр сервиса в локальной ветке:

```powershell
cd ../service
$env:DB_NETWORK='warehouse-tier3-local-branch'
$env:DB_WRITE_HOSTS='pg-3'
$env:DB_READ_HOSTS='pg-3'
$env:API_PORT='8001'
$env:APP_NODE='local'
docker compose -p warehouse-local up -d api
```

3. Изолируйте `pg-3` от основной сети, повысьте его только для учебного опыта и
   запишите разные `/api/demo/events` через порты 8000 и 8001.
4. Не пытайтесь физически объединить timelines. Выберите канонический primary,
   а append-only события перенесите прикладным скриптом:

```powershell
docker compose run --rm --no-deps api python scripts/reconcile_events.py `
  --source-host pg-3 --target-host pg-1 --dry-run
```

После проверки повторите без `--dry-run`, затем пересоздайте проигравшую ветку
как standby. UUID события делает повторный импорт идемпотентным. Такой подход
подходит лишь к специально спроектированным событиям; произвольные UPDATE и
конфликты constraints требуют бизнес-правил и не сливаются автоматически.
