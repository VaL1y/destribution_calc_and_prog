FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Приложение из tier_2 намеренно переиспользуется: в tier_3 мы меняем
# архитектуру БД, а не переписываем складской сервис.
COPY tier_2/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY tier_2/api/app ./app
COPY tier_2/api/scripts ./scripts

# Этот файл заменяет только подключение к БД: чтение и запись получают
# разные правила выбора PostgreSQL-ноды.
COPY tier_3/api/db.py ./app/db.py
COPY tier_3/api/tier3_main.py ./tier3_main.py
COPY tier_3/scripts ./tier3_scripts

# В исходном API все операции используют один engine. Для tier_3 основной
# engine остаётся write-pool, а только helper read_connection получает
# read_engine. Так /api/status действительно проверяет доступность записи.
RUN sed -i 's/from \.db import engine/from .db import engine, read_engine/' app/main.py \
    && sed -i '/def read_connection()/,/except OperationalError/ s/with engine.connect() as connection:/with read_engine.connect() as connection:/' app/main.py

EXPOSE 8000

CMD ["uvicorn", "tier3_main:app", "--host", "0.0.0.0", "--port", "8000"]
