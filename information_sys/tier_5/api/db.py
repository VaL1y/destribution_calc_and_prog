import os

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine


def make_engine(hosts: str, target_session_attrs: str) -> Engine:
    """Build a pool that discovers the node role through libpq."""
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
            "port": os.getenv("DB_PORTS", "5433,5434,5432"),
            "connect_timeout": 2,
            "target_session_attrs": target_session_attrs,
        },
    )


write_engine = make_engine(os.environ["DB_WRITE_HOSTS"], "read-write")
read_engine = make_engine(os.environ["DB_READ_HOSTS"], "prefer-standby")
engine = write_engine

