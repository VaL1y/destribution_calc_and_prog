FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY tier_2/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY tier_2/api/app ./app
COPY tier_4/api/db.py ./app/db.py

# Reads use prefer-standby; writes and /api/status keep using the primary pool.
RUN sed -i 's/from \.db import engine/from .db import engine, read_engine/' app/main.py \
    && sed -i '/def read_connection()/,/except OperationalError/ s/with engine.connect() as connection:/with read_engine.connect() as connection:/' app/main.py

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

