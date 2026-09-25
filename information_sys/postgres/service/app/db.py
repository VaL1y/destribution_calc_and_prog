import os

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine


def _ports_for(hosts: str) -> str:
    ports = [part.strip() for part in os.getenv("DB_PORTS", "5432").split(",") if part.strip()]
    host_count = len([part for part in hosts.split(",") if part.strip()])
    if len(ports) == 1 and host_count > 1:
        ports *= host_count
    return ",".join(ports)


def make_engine(hosts: str, target_session_attrs: str) -> Engine:
    """Create a pool using libpq multi-host connection semantics."""
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
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "3")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "300")),
        connect_args={
            "host": hosts,
            "port": _ports_for(hosts),
            "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "2")),
            "target_session_attrs": target_session_attrs,
        },
    )


write_engine = make_engine(
    os.getenv("DB_WRITE_HOSTS", os.getenv("DB_HOST", "pg-1")),
    "read-write",
)
read_engine = make_engine(
    os.getenv("DB_READ_HOSTS", os.getenv("DB_WRITE_HOSTS", os.getenv("DB_HOST", "pg-1"))),
    os.getenv("DB_READ_TARGET", "prefer-standby"),
)

# Compatibility name used by the CRUD endpoints. It always targets a primary.
engine = write_engine
