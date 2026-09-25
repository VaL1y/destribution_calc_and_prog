import os
import random

import requests
from locust import HttpUser, between, events, task


TARGET_HOST = os.getenv("TARGET_HOST", "http://api:8000")
LOAD_PRODUCT_COUNT = int(os.getenv("LOAD_PRODUCT_COUNT", "32"))
LOAD_SKU_PREFIX = "LOAD-"
load_product_id: int | None = None
load_product_ids: list[int] = []


def ensure_load_products() -> list[int]:
    """Create isolated products used by write scenarios."""
    response = requests.get(f"{TARGET_HOST}/api/products", timeout=10)
    response.raise_for_status()
    products_by_sku = {item["sku"]: item["id"] for item in response.json()["items"]}
    product_ids: list[int] = []

    for number in range(LOAD_PRODUCT_COUNT):
        sku = f"{LOAD_SKU_PREFIX}{number:03d}"
        product_id = products_by_sku.get(sku)
        if product_id is None:
            response = requests.post(
                f"{TARGET_HOST}/api/products",
                json={
                    "sku": sku,
                    "name": f"Нагрузочный товар {number:03d}",
                    "category_id": 1,
                    "unit": "шт.",
                    "quantity": 1_000_000,
                    "reorder_level": 0,
                },
                timeout=10,
            )
            response.raise_for_status()
            product_id = response.json()["id"]
        product_ids.append(product_id)

    return product_ids


@events.test_start.add_listener
def prepare_test(environment, **kwargs):
    global load_product_id, load_product_ids
    if environment.runner is None or environment.runner.__class__.__name__ != "WorkerRunner":
        load_product_ids = ensure_load_products()
        load_product_id = load_product_ids[0]


class WarehouseUser(HttpUser):
    abstract = True
    host = TARGET_HOST


class ReadOnlyUser(WarehouseUser):
    """Typical catalogue and journal browsing."""

    wait_time = between(0.05, 0.20)

    @task(6)
    def products(self):
        self.client.get("/api/products", name="GET /api/products")

    @task(3)
    def movements(self):
        self.client.get("/api/movements?limit=20", name="GET /api/movements")

    @task(1)
    def categories(self):
        self.client.get("/api/categories", name="GET /api/categories")


class HotProductWriter(WarehouseUser):
    """Concurrent arrivals for one SKU: deliberately creates a row-lock hotspot."""

    wait_time = between(0.01, 0.03)

    @task
    def receive_one_unit(self):
        if load_product_id is None:
            return
        self.client.post(
            "/api/movements",
            name="POST /api/movements [same product]",
            json={
                "product_id": load_product_id,
                "movement_type": "in",
                "quantity": 1,
                "note": "Locust load test",
            },
        )


class ParallelProductWriter(WarehouseUser):
    """Arrivals spread over many SKUs to measure write throughput without one hot row."""

    wait_time = between(0.01, 0.03)

    @task
    def receive_one_unit(self):
        if not load_product_ids:
            return
        self.client.post(
            "/api/movements",
            name="POST /api/movements [many products]",
            json={
                "product_id": random.choice(load_product_ids),
                "movement_type": "in",
                "quantity": 1,
                "note": "Locust single-node benchmark",
            },
        )


class MixedWarehouseUser(WarehouseUser):
    """80% reads and 20% writes, close to a small warehouse workload."""

    wait_time = between(0.03, 0.12)

    @task(6)
    def products(self):
        self.client.get("/api/products", name="GET /api/products")

    @task(2)
    def movements(self):
        self.client.get("/api/movements?limit=20", name="GET /api/movements")

    @task(2)
    def receive_one_unit(self):
        if not load_product_ids:
            return
        self.client.post(
            "/api/movements",
            name="POST /api/movements [mixed]",
            json={
                "product_id": random.choice(load_product_ids),
                "movement_type": "in",
                "quantity": 1,
                "note": "Locust mixed test",
            },
        )
