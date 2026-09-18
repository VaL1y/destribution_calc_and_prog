import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def make_engine(url: str) -> Engine:
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_POOL_SIZE", "12")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "3")),
        pool_recycle=60,
        connect_args={"connect_timeout": 2},
    )


engine = make_engine(
    os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://warehouse:warehouse@localhost:5432/warehouse",
    )
)
