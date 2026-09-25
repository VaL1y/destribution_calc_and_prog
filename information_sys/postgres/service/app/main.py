from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from .db import engine, read_engine


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Мини-склад API",
    description="Учебный CRUD для PostgreSQL с ограниченными ресурсами.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

from .demo import router as demo_router  # noqa: E402

app.include_router(demo_router)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    category_id: int = Field(gt=0)
    unit: str = Field(default="шт.", min_length=1, max_length=20)
    quantity: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=5, ge=0)


class ProductUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category_id: int = Field(gt=0)
    unit: str = Field(min_length=1, max_length=20)
    reorder_level: int = Field(ge=0)


class MovementCreate(BaseModel):
    product_id: int = Field(gt=0)
    movement_type: Literal["in", "out"]
    quantity: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=250)


@contextmanager
def read_connection():
    try:
        with read_engine.connect() as connection:
            yield connection
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="База данных недоступна",
        ) from exc


def row_dict(row) -> dict:
    return dict(row._mapping)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/status")
def database_status() -> dict:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return {"database": {"available": True, "writable": True}}
    except Exception:
        return {"database": {"available": False, "writable": False}}


@app.get("/api/categories")
def list_categories(response: Response) -> list[dict]:
    with read_connection() as connection:
        rows = connection.execute(
            text("SELECT id, name FROM warehouse.categories ORDER BY name")
        )
        return [row_dict(row) for row in rows]


@app.post("/api/categories", status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate) -> dict:
    try:
        with engine.begin() as connection:
            row = connection.execute(
                text(
                    "INSERT INTO warehouse.categories(name) VALUES (:name) "
                    "RETURNING id, name"
                ),
                {"name": payload.name.strip()},
            ).one()
            return row_dict(row)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Такая категория уже существует") from exc
    except OperationalError as exc:
        raise HTTPException(status_code=503, detail="Основная БД недоступна: запись невозможна") from exc


@app.get("/api/products")
def list_products(response: Response) -> dict:
    query = text(
        """
        SELECT p.id, p.sku, p.name, p.category_id, c.name AS category,
               p.unit, p.quantity, p.reorder_level, p.updated_at,
               p.quantity <= p.reorder_level AS low_stock
        FROM warehouse.products p
        JOIN warehouse.categories c ON c.id = p.category_id
        ORDER BY p.name
        """
    )
    with read_connection() as connection:
        rows = connection.execute(query)
        return {"items": [row_dict(row) for row in rows]}


@app.post("/api/products", status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate) -> dict:
    query = text(
        """
        INSERT INTO warehouse.products
            (sku, name, category_id, unit, quantity, reorder_level)
        VALUES
            (:sku, :name, :category_id, :unit, :quantity, :reorder_level)
        RETURNING id, sku, name, category_id, unit, quantity, reorder_level
        """
    )
    try:
        with engine.begin() as connection:
            row = connection.execute(query, payload.model_dump()).one()
            if payload.quantity:
                connection.execute(
                    text(
                        "INSERT INTO warehouse.stock_movements"
                        "(product_id, movement_type, quantity, note) "
                        "VALUES (:product_id, 'in', :quantity, 'Начальный остаток')"
                    ),
                    {"product_id": row.id, "quantity": payload.quantity},
                )
            return row_dict(row)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Проверьте SKU и категорию") from exc
    except OperationalError as exc:
        raise HTTPException(status_code=503, detail="Основная БД недоступна: запись невозможна") from exc


@app.put("/api/products/{product_id}")
def update_product(product_id: int, payload: ProductUpdate) -> dict:
    query = text(
        """
        UPDATE warehouse.products
        SET name = :name, category_id = :category_id, unit = :unit,
            reorder_level = :reorder_level, updated_at = now()
        WHERE id = :product_id
        RETURNING id, sku, name, category_id, unit, quantity, reorder_level
        """
    )
    try:
        with engine.begin() as connection:
            row = connection.execute(
                query, {**payload.model_dump(), "product_id": product_id}
            ).one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Товар не найден")
            return row_dict(row)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Категория не существует") from exc
    except OperationalError as exc:
        raise HTTPException(status_code=503, detail="Основная БД недоступна: запись невозможна") from exc


@app.delete("/api/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int) -> Response:
    try:
        with engine.begin() as connection:
            deleted = connection.execute(
                text("DELETE FROM warehouse.products WHERE id = :id RETURNING id"),
                {"id": product_id},
            ).one_or_none()
            if deleted is None:
                raise HTTPException(status_code=404, detail="Товар не найден")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except OperationalError as exc:
        raise HTTPException(status_code=503, detail="Основная БД недоступна: удаление невозможно") from exc


@app.get("/api/movements")
def list_movements(response: Response, limit: int = 20) -> list[dict]:
    query = text(
        """
        SELECT m.id, m.product_id, p.name AS product, m.movement_type,
               m.quantity, m.note, m.created_at
        FROM warehouse.stock_movements m
        JOIN warehouse.products p ON p.id = m.product_id
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT :limit
        """
    )
    with read_connection() as connection:
        rows = connection.execute(query, {"limit": max(1, min(limit, 100))})
        return [row_dict(row) for row in rows]


@app.post("/api/movements", status_code=status.HTTP_201_CREATED)
def create_movement(payload: MovementCreate) -> dict:
    delta = payload.quantity if payload.movement_type == "in" else -payload.quantity
    try:
        with engine.begin() as connection:
            product = connection.execute(
                text(
                    "SELECT id, quantity FROM warehouse.products "
                    "WHERE id = :id FOR UPDATE"
                ),
                {"id": payload.product_id},
            ).one_or_none()
            if product is None:
                raise HTTPException(status_code=404, detail="Товар не найден")
            if product.quantity + delta < 0:
                raise HTTPException(status_code=409, detail="Недостаточно товара для списания")

            row = connection.execute(
                text(
                    """
                    INSERT INTO warehouse.stock_movements
                        (product_id, movement_type, quantity, note)
                    VALUES (:product_id, :movement_type, :quantity, :note)
                    RETURNING id, product_id, movement_type, quantity, note, created_at
                    """
                ),
                payload.model_dump(),
            ).one()
            connection.execute(
                text(
                    "UPDATE warehouse.products "
                    "SET quantity = quantity + :delta, updated_at = now() "
                    "WHERE id = :id"
                ),
                {"delta": delta, "id": payload.product_id},
            )
            return row_dict(row)
    except OperationalError as exc:
        raise HTTPException(status_code=503, detail="Основная БД недоступна: операция невозможна") from exc
