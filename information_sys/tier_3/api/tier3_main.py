import os
from uuid import uuid4

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.db import read_engine, write_engine
from app.main import app


class InventoryEventCreate(BaseModel):
    product_id: int = Field(gt=0)
    delta: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=250)


def event_dict(row) -> dict:
    return dict(row._mapping)


@app.get("/api/demo/node")
def demo_node() -> dict:
    try:
        with write_engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT pg_is_in_recovery() AS in_recovery,
                           current_setting('server_version') AS postgres_version,
                           inet_server_addr()::text AS server_address
                    """
                )
            ).one()
        return {
            "application_node": os.getenv("APP_NODE", "unknown"),
            "database": event_dict(row),
        }
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Для этой ветки сейчас нет доступного writable primary",
        ) from exc


@app.post("/api/demo/events", status_code=status.HTTP_201_CREATED)
def create_inventory_event(payload: InventoryEventCreate) -> dict:
    event_id = uuid4()
    try:
        with write_engine.begin() as connection:
            row = connection.execute(
                text(
                    """
                    INSERT INTO warehouse.inventory_events
                        (event_id, source_node, product_id, delta, note)
                    VALUES
                        (:event_id, :source_node, :product_id, :delta, :note)
                    RETURNING event_id, source_node, product_id, delta, note,
                              created_at
                    """
                ),
                {
                    "event_id": event_id,
                    "source_node": os.getenv("APP_NODE", "unknown"),
                    **payload.model_dump(),
                },
            ).one()
        return event_dict(row)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Товар не существует или событие нарушает constraint",
        ) from exc
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Для этой ветки сейчас нет доступного writable primary",
        ) from exc


@app.get("/api/demo/events")
def list_inventory_events(limit: int = 100) -> dict:
    with read_engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT event_id, source_node, product_id, delta, note, created_at
                FROM warehouse.inventory_events
                ORDER BY created_at, event_id
                LIMIT :limit
                """
            ),
            {"limit": max(1, min(limit, 1000))},
        )
        items = [event_dict(row) for row in rows]
    return {
        "application_node": os.getenv("APP_NODE", "unknown"),
        "items": items,
        "total_delta": sum(item["delta"] for item in items),
    }
