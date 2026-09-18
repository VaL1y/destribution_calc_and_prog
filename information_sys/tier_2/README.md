# Учебный модуль складского учёта

Небольшая система на FastAPI и PostgreSQL: категории, товары, приход и списание. База данных намеренно ограничена по CPU, памяти и числу подключений, чтобы на следующих этапах исследовать поведение системы под нагрузкой и при отказах.

## Состав

- `db` — PostgreSQL, порт `5432`, лимит `0.5 CPU / 256 MB`, максимум 40 подключений;
- `api` — FastAPI и веб-интерфейс, порт `8000`, два Uvicorn workers;
- схема PostgreSQL `warehouse`: `categories`, `products`, `stock_movements`.

## Запуск

```powershell
docker compose up --build -d
```

После запуска:

- интерфейс: <http://localhost:8000>
- Swagger API: <http://localhost:8000/docs>
- проверка БД: <http://localhost:8000/api/status>

Настройки можно переопределить: скопировать `.env.example` в `.env` и изменить значения. Чтобы заново выполнить init-скрипты, удалить только volumes этого проекта командой `docker compose down -v` — все учебные данные будут потеряны.

## Демонстрация отказа базы данных

Запустить систему и убедиться, что БД доступна:

```powershell
docker compose up --build -d
docker compose ps
```

Остановить PostgreSQL:

```powershell
docker compose stop db
```

Страница FastAPI останется доступной, но чтение и запись данных начнут возвращать `503`, а индикатор DATABASE покажет недоступность. Это базовый пример единой точки отказа; репликацию и автоматическое переключение можно добавить отдельным следующим этапом.

Вернуть PostgreSQL:

```powershell
docker compose start db
```

## Демонстрация лимита подключений

PostgreSQL настроена на 40 подключений. Следующая команда попробует удерживать 45 соединений 60 секунд:

```powershell
docker compose exec api python scripts/hold_connections.py 45 60
```

Часть соединений будет отклонена, а API в этот момент может временно отвечать ошибкой. Уменьшить или увеличить нагрузку можно первым аргументом, время удержания — вторым.

## Нагрузочное тестирование Locust

Locust находится в отдельном Compose-профиле и не запускается вместе с обычным приложением.

Интерактивный режим:

```powershell
docker compose --profile load up -d
```

Открыть <http://localhost:8089>, указать число пользователей, скорость их запуска и выбрать сценарий:

- `ReadOnlyUser` — чтение товаров, категорий и журнала;
- `HotProductWriter` — конкурентные приходы одного товара, создающие горячую строку;
- `ParallelProductWriter` — приходы распределяются по 32 товарам;
- `MixedWarehouseUser` — примерно 80% чтения и 20% записи.

Пример автоматического теста чтения, 30 пользователей на 30 секунд:

```powershell
docker compose --profile load run --rm locust `
  -f /mnt/locust/locustfile.py --host http://api:8000 `
  --headless -u 30 -r 5 -t 30s --csv /results/read-30 ReadOnlyUser
```

Пример проверки конкурентной записи:

```powershell
docker compose --profile load run --rm locust `
  -f /mnt/locust/locustfile.py --host http://api:8000 `
  --headless -u 20 -r 5 -t 30s --csv /results/write-20 HotProductWriter
```

Результаты CSV сохраняются в `load-results`. Сценарии записи используют отдельную позицию `LOAD-TEST`. Удалить её вместе с тестовым журналом:

```powershell
docker compose exec db psql -U warehouse -d warehouse -c `
  "DELETE FROM warehouse.products WHERE sku = 'LOAD-TEST';"
```

Результаты контрольного прогона и найденные узкие места описаны в [`LOAD_TEST_REPORT.md`](LOAD_TEST_REPORT.md).

### Сравнение количества FastAPI workers

Количество процессов API задаётся переменной `API_WORKERS` и по умолчанию равно `2`. Каждый worker имеет собственный пул PostgreSQL `12+3`.

Контрольный benchmark одной PostgreSQL — ступени чтения и параллельной записи:

```powershell
.\load-tests\benchmark-single-node.ps1
```

Скрипт очищает только данные с SKU `LOAD-%`, перезапускает API перед каждой ступенью и печатает итоговую таблицу. Baseline текущего локального контура: около `340 RPS` чтения при `p95 ≈ 51 мс` и `355 RPS` записи при `p95 ≈ 78 мс`. Подробности и точки перегрузки находятся в [`LOAD_TEST_REPORT.md`](LOAD_TEST_REPORT.md).

Автоматическое сравнение 1, 2 и 4 workers:

```powershell
.\load-tests\compare-workers.ps1
```

Параметры теста можно изменить:

```powershell
.\load-tests\compare-workers.ps1 -Users 150 -SpawnRate 50 -Duration 30s
```

После прогона скрипт возвращает API к двум workers. CSV сохраняются как `load-results/workers-*_stats.csv`.

## Остановка

```powershell
docker compose down
```

Volumes сохраняются. Для полного удаления учебных данных добавить флаг `-v`.
