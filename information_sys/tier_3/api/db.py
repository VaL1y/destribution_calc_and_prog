import os

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine


def make_engine(hosts: str, target_session_attrs: str) -> Engine:
    """Create a libpq multi-host connection pool.

    read-write finds the current primary. prefer-standby prefers a replica,
    but can fall back to the primary when every replica is unavailable.
    """
    ports = os.getenv("DB_PORTS", "5432,5432,5432")
    url = URL.create(
        "postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "warehouse"),
        password=os.getenv("POSTGRES_PASSWORD", "warehouse"),
        database=os.getenv("POSTGRES_DB", "warehouse"),
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_POOL_SIZE", "12")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "3")),
        pool_recycle=30,
        connect_args={
            "host": hosts,
            "port": ports,
            "connect_timeout": 2,
            "target_session_attrs": target_session_attrs,
        },
    )


write_engine = make_engine(
    os.getenv("DB_WRITE_HOSTS", "pg-1,pg-2,pg-3"),
    "read-write",
)
read_engine = make_engine(
    os.getenv("DB_READ_HOSTS", "pg-2,pg-3,pg-1"),
    "prefer-standby",
)

# Backwards-compatible name used by the tier_2 application. It deliberately
# points to the primary: writes and /api/status must test a writable database.
engine = write_engine
