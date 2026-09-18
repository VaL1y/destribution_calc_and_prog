from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import argparse
import json
import os
import random
import shutil
import threading
import time
import tracemalloc
from multiprocessing import Process, Queue
from pathlib import Path
from queue import Empty


BASE_DIR = Path(__file__).parent
CLIENTS_FILE = "data_clients"
GOODS_FILE = "data_goods"
BUYES_FILE = "data_buyes"
MONEY_FILE = "data_money"
LOCK_DIR = ".data_lock"


@dataclass
class Client:
    id: int
    name: str


@dataclass
class Good:
    id: int
    name: str
    price: float


@dataclass
class Buy:
    id: int
    cl_id: int
    good_id: int
    count: int
    total: float
    date: str


@dataclass
class Money:
    id: int
    date: str
    money: float


### step 1 - in-memory ###


class InMemorySystem:
    def __init__(self) -> None:
        self.clients: dict[int, Client] = {}
        self.goods: dict[int, Good] = {}
        self.buys: dict[int, Buy] = {}
        self.money: dict[int, Money] = {}

        self.next_client_id = 1
        self.next_good_id = 1
        self.next_buy_id = 1
        self.next_money_id = 1

        self.lock = threading.RLock()

    def create_client(self, name: str) -> Client:
        with self.lock:
            item = Client(id=self.next_client_id, name=name)
            self.clients[item.id] = item
            self.next_client_id += 1
            return item

    def get_client(self, client_id: int) -> Client | None:
        with self.lock:
            return self.clients.get(client_id)

    def list_clients(self) -> dict[str, object]:
        with self.lock:
            items = list(self.clients.values())
            return {"count": len(items), "items": items}

    def delete_client(self, client_id: int) -> bool:
        with self.lock:
            return self.clients.pop(client_id, None) is not None

    def create_good(self, name: str, price: float) -> Good:
        with self.lock:
            item = Good(id=self.next_good_id, name=name, price=float(price))
            self.goods[item.id] = item
            self.next_good_id += 1
            return item

    def get_good(self, good_id: int) -> Good | None:
        with self.lock:
            return self.goods.get(good_id)

    def list_goods(self) -> dict[str, object]:
        with self.lock:
            items = list(self.goods.values())
            return {"count": len(items), "items": items}

    def delete_good(self, good_id: int) -> bool:
        with self.lock:
            return self.goods.pop(good_id, None) is not None

    def create_buy(
        self,
        cl_id: int,
        good_id: int,
        count: int,
        buy_date: str | None = None,
    ) -> Buy:
        with self.lock:
            if cl_id not in self.clients:
                raise ValueError("Client not found")
            if good_id not in self.goods:
                raise ValueError("Good not found")

            good = self.goods[good_id]
            item = Buy(
                id=self.next_buy_id,
                cl_id=cl_id,
                good_id=good_id,
                count=int(count),
                total=good.price * int(count),
                date=buy_date or str(date.today()),
            )

            self.buys[item.id] = item
            self.next_buy_id += 1
            return item

    def find_buys_by_cl_id(self, cl_id: int) -> list[Buy]:
        with self.lock:
            return [item for item in self.buys.values() if item.cl_id == cl_id]

    def update_buy(self, buy_id: int, **fields: object) -> Buy | None:
        with self.lock:
            old = self.buys.get(buy_id)
            if old is None:
                return None

            data = asdict(old)
            data.update(fields)
            data["id"] = buy_id
            data["count"] = int(data["count"])

            if data["cl_id"] not in self.clients:
                raise ValueError("Client not found")
            if data["good_id"] not in self.goods:
                raise ValueError("Good not found")

            good = self.goods[int(data["good_id"])]
            data["total"] = good.price * int(data["count"])

            updated = Buy(**data)
            self.buys[buy_id] = updated
            return updated

    def delete_buy(self, buy_id: int) -> bool:
        with self.lock:
            return self.buys.pop(buy_id, None) is not None

    def create_money(self, money_date: str, money: float | None = None) -> Money:
        with self.lock:
            if self.get_money_by_date(money_date) is not None:
                raise ValueError("Money record for this date already exists")

            value = self.calc_money(money_date) if money is None else float(money)
            item = Money(id=self.next_money_id, date=money_date, money=value)

            self.money[item.id] = item
            self.next_money_id += 1
            return item

    def calc_money(self, money_date: str) -> float:
        with self.lock:
            return sum(item.total for item in self.buys.values() if item.date == money_date)

    def get_money_by_date(self, money_date: str) -> Money | None:
        with self.lock:
            for item in self.money.values():
                if item.date == money_date:
                    return item
            return None

    def update_money(self, money_id: int, **fields: object) -> Money | None:
        with self.lock:
            old = self.money.get(money_id)
            if old is None:
                return None

            data = asdict(old)
            data.update(fields)
            data["id"] = money_id
            data["money"] = float(data["money"])

            new_date = str(data["date"])
            for item in self.money.values():
                if item.id != money_id and item.date == new_date:
                    raise ValueError("Money record for this date already exists")

            updated = Money(**data)
            self.money[money_id] = updated
            return updated


### step 2 - in files ###


class DirectoryLock:
    def __init__(
        self,
        lock_path: Path,
        timeout: float = 30.0,
        interval: float = 0.01,
        stale_after: float = 120.0,
    ) -> None:
        self.lock_path = lock_path
        self.timeout = timeout
        self.interval = interval
        self.stale_after = stale_after

    def __enter__(self) -> DirectoryLock:
        start = time.perf_counter()

        while True:
            try:
                os.mkdir(self.lock_path)
                return self
            except FileExistsError:
                if self._is_stale():
                    shutil.rmtree(self.lock_path, ignore_errors=True)
                    continue
                if time.perf_counter() - start > self.timeout:
                    raise TimeoutError(f"Could not acquire file lock: {self.lock_path}")
                time.sleep(self.interval)

    def __exit__(self, exc_type, exc, tb) -> None:
        shutil.rmtree(self.lock_path, ignore_errors=True)

    def _is_stale(self) -> bool:
        try:
            age = time.time() - self.lock_path.stat().st_mtime
        except FileNotFoundError:
            return False
        return age > self.stale_after


class JsonFileSystem:
    def __init__(self, base_dir: Path | str = BASE_DIR) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.paths = {
            "clients": self.base_dir / CLIENTS_FILE,
            "goods": self.base_dir / GOODS_FILE,
            "buys": self.base_dir / BUYES_FILE,
            "money": self.base_dir / MONEY_FILE,
        }

        for path in self.paths.values():
            path.touch(exist_ok=True)

        self.lock_path = self.base_dir / LOCK_DIR

    def _lock(self) -> DirectoryLock:
        return DirectoryLock(self.lock_path)

    def _load(self, name: str, model):
        path = self.paths[name]
        if not path.exists() or path.stat().st_size == 0:
            return []

        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return [model(**item) for item in data]

    def _save(self, name: str, items: list[object]) -> None:
        path = self.paths[name]
        temp_path = path.with_name(
            f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )

        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump([asdict(item) for item in items], file, ensure_ascii=False, indent=4)

        os.replace(temp_path, path)

    def _next_id(self, items: list[object]) -> int:
        return max((item.id for item in items), default=0) + 1

    def create_client(self, name: str) -> Client:
        with self._lock():
            items = self._load("clients", Client)
            item = Client(id=self._next_id(items), name=name)
            items.append(item)
            self._save("clients", items)
            return item

    def get_client(self, client_id: int) -> Client | None:
        with self._lock():
            for item in self._load("clients", Client):
                if item.id == client_id:
                    return item
            return None

    def list_clients(self) -> dict[str, object]:
        with self._lock():
            items = self._load("clients", Client)
            return {"count": len(items), "items": items}

    def delete_client(self, client_id: int) -> bool:
        with self._lock():
            items = self._load("clients", Client)
            new_items = [item for item in items if item.id != client_id]
            self._save("clients", new_items)
            return len(new_items) != len(items)

    def create_good(self, name: str, price: float) -> Good:
        with self._lock():
            items = self._load("goods", Good)
            item = Good(id=self._next_id(items), name=name, price=float(price))
            items.append(item)
            self._save("goods", items)
            return item

    def get_good(self, good_id: int) -> Good | None:
        with self._lock():
            for item in self._load("goods", Good):
                if item.id == good_id:
                    return item
            return None

    def list_goods(self) -> dict[str, object]:
        with self._lock():
            items = self._load("goods", Good)
            return {"count": len(items), "items": items}

    def delete_good(self, good_id: int) -> bool:
        with self._lock():
            items = self._load("goods", Good)
            new_items = [item for item in items if item.id != good_id]
            self._save("goods", new_items)
            return len(new_items) != len(items)

    def create_buy(
        self,
        cl_id: int,
        good_id: int,
        count: int,
        buy_date: str | None = None,
    ) -> Buy:
        with self._lock():
            clients = self._load("clients", Client)
            goods = self._load("goods", Good)
            buys = self._load("buys", Buy)

            if not any(item.id == cl_id for item in clients):
                raise ValueError("Client not found")

            good = next((item for item in goods if item.id == good_id), None)
            if good is None:
                raise ValueError("Good not found")

            item = Buy(
                id=self._next_id(buys),
                cl_id=cl_id,
                good_id=good_id,
                count=int(count),
                total=good.price * int(count),
                date=buy_date or str(date.today()),
            )

            buys.append(item)
            self._save("buys", buys)
            return item

    def find_buys_by_cl_id(self, cl_id: int) -> list[Buy]:
        with self._lock():
            return [item for item in self._load("buys", Buy) if item.cl_id == cl_id]

    def update_buy(self, buy_id: int, **fields: object) -> Buy | None:
        with self._lock():
            clients = self._load("clients", Client)
            goods = self._load("goods", Good)
            buys = self._load("buys", Buy)

            for index, old in enumerate(buys):
                if old.id != buy_id:
                    continue

                data = asdict(old)
                data.update(fields)
                data["id"] = buy_id
                data["count"] = int(data["count"])

                if not any(item.id == data["cl_id"] for item in clients):
                    raise ValueError("Client not found")

                good = next((item for item in goods if item.id == data["good_id"]), None)
                if good is None:
                    raise ValueError("Good not found")

                data["total"] = good.price * int(data["count"])
                updated = Buy(**data)
                buys[index] = updated
                self._save("buys", buys)
                return updated

            return None

    def delete_buy(self, buy_id: int) -> bool:
        with self._lock():
            items = self._load("buys", Buy)
            new_items = [item for item in items if item.id != buy_id]
            self._save("buys", new_items)
            return len(new_items) != len(items)

    def create_money(self, money_date: str, money: float | None = None) -> Money:
        with self._lock():
            items = self._load("money", Money)

            if any(item.date == money_date for item in items):
                raise ValueError("Money record for this date already exists")

            value = self._calc_money_locked(money_date) if money is None else float(money)
            item = Money(id=self._next_id(items), date=money_date, money=value)

            items.append(item)
            self._save("money", items)
            return item

    def calc_money(self, money_date: str) -> float:
        with self._lock():
            return self._calc_money_locked(money_date)

    def _calc_money_locked(self, money_date: str) -> float:
        return sum(
            item.total
            for item in self._load("buys", Buy)
            if item.date == money_date
        )

    def get_money_by_date(self, money_date: str) -> Money | None:
        with self._lock():
            for item in self._load("money", Money):
                if item.date == money_date:
                    return item
            return None

    def update_money(self, money_id: int, **fields: object) -> Money | None:
        with self._lock():
            items = self._load("money", Money)

            for index, old in enumerate(items):
                if old.id != money_id:
                    continue

                data = asdict(old)
                data.update(fields)
                data["id"] = money_id
                data["money"] = float(data["money"])
                new_date = str(data["date"])

                if any(item.id != money_id and item.date == new_date for item in items):
                    raise ValueError("Money record for this date already exists")

                updated = Money(**data)
                items[index] = updated
                self._save("money", items)
                return updated

            return None


def upsert_money_for_date(system, money_date: str) -> Money:
    value = system.calc_money(money_date)
    item = system.get_money_by_date(money_date)

    if item is None:
        return system.create_money(money_date, value)

    updated = system.update_money(item.id, money=value)
    if updated is None:
        raise RuntimeError("Money record disappeared during update")
    return updated


def scenario(system, operations: int, worker_id: int, work_date: str) -> None:
    for index in range(operations):
        client = system.create_client(f"client_{worker_id}_{index}")
        good = system.create_good(
            f"good_{worker_id}_{index}",
            random.randint(10, 1000),
        )
        buy = system.create_buy(
            cl_id=client.id,
            good_id=good.id,
            count=random.randint(1, 10),
            buy_date=work_date,
        )

        if index % 5 == 0:
            system.find_buys_by_cl_id(client.id)

        if index % 10 == 0:
            system.update_buy(buy.id, count=random.randint(1, 20))

        if index % 20 == 0:
            upsert_money_for_date(system, work_date)

        if index % 30 == 0:
            system.delete_buy(buy.id)


def run_threads_test(system, workers: int, operations: int) -> dict[str, object]:
    work_date = str(date.today())
    tracemalloc.start()
    start = time.perf_counter()
    errors = []

    def worker(worker_id: int) -> None:
        try:
            scenario(system, operations, worker_id, work_date)
        except Exception as exc:
            errors.append(repr(exc))

    threads = [
        threading.Thread(target=worker, args=(worker_id,))
        for worker_id in range(workers)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "mode": "threads",
        "workers": workers,
        "operations_per_worker": operations,
        "total_operations": workers * operations,
        "seconds": round(time.perf_counter() - start, 4),
        "memory_current_mb": round(current / 1024 / 1024, 4),
        "memory_peak_mb": round(peak / 1024 / 1024, 4),
        "errors": errors,
    }


def _process_worker(
    base_dir: str,
    operations: int,
    worker_id: int,
    work_date: str,
    queue: Queue,
) -> None:
    tracemalloc.start()
    start = time.perf_counter()
    errors = []

    try:
        system = JsonFileSystem(base_dir)
        scenario(system, operations, worker_id, work_date)
    except Exception as exc:
        errors.append(repr(exc))

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    queue.put(
        {
            "worker_id": worker_id,
            "seconds": round(time.perf_counter() - start, 4),
            "memory_current_mb": round(current / 1024 / 1024, 4),
            "memory_peak_mb": round(peak / 1024 / 1024, 4),
            "errors": errors,
        }
    )


def run_processes_file_test(
    base_dir: Path,
    workers: int,
    operations: int,
) -> dict[str, object]:
    work_date = str(date.today())
    queue = Queue()
    start = time.perf_counter()

    processes = [
        (
            worker_id,
            Process(
            target=_process_worker,
            args=(str(base_dir), operations, worker_id, work_date, queue),
            ),
        )
        for worker_id in range(workers)
    ]

    for _, process in processes:
        process.start()

    for _, process in processes:
        process.join()

    queued_results = {}
    for _ in processes:
        try:
            result = queue.get(timeout=0.2)
            queued_results[result["worker_id"]] = result
        except Empty:
            break

    results = []
    for worker_id, process in processes:
        result = queued_results.get(
            worker_id,
            {
                "worker_id": worker_id,
                "seconds": None,
                "memory_current_mb": None,
                "memory_peak_mb": None,
                "errors": ["worker did not report"],
            },
        )
        result["exit_code"] = process.exitcode
        results.append(result)

    system = JsonFileSystem(base_dir)
    return {
        "mode": "processes_file",
        "workers": workers,
        "operations_per_worker": operations,
        "total_operations": workers * operations,
        "seconds": round(time.perf_counter() - start, 4),
        "worker_results": results,
        "clients": system.list_clients()["count"],
        "goods": system.list_goods()["count"],
        "money": system.get_money_by_date(work_date),
    }


def prepare_loadtest_dir(base_dir: Path) -> Path:
    path = base_dir / "loadtest_data"
    if path.exists():
        shutil.rmtree(path)

    path.mkdir(parents=True)
    for file_name in (CLIENTS_FILE, GOODS_FILE, BUYES_FILE, MONEY_FILE):
        (path / file_name).touch()

    return path


def parse_int_steps(value: str) -> list[int]:
    steps = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        number = int(part)
        if number <= 0:
            raise ValueError("Stress steps must be positive integers")
        steps.append(number)

    if not steps:
        raise ValueError("At least one stress step is required")

    return steps


def collect_report_errors(report: dict[str, object]) -> list[str]:
    errors = list(report.get("errors") or [])

    for worker_result in report.get("worker_results") or []:
        errors.extend(worker_result.get("errors") or [])
        if worker_result.get("exit_code") not in (0, None):
            errors.append(f"worker {worker_result['worker_id']} exit code "
                          f"{worker_result['exit_code']}")

    return errors


def report_peak_memory(report: dict[str, object]) -> float | None:
    if report.get("memory_peak_mb") is not None:
        return float(report["memory_peak_mb"])

    worker_results = report.get("worker_results") or []
    peaks = [
        worker_result["memory_peak_mb"]
        for worker_result in worker_results
        if worker_result.get("memory_peak_mb") is not None
    ]

    if not peaks:
        return None

    return float(max(peaks))


def run_backend_once(
    backend: str,
    workers: int,
    operations: int,
) -> dict[str, object]:
    if backend == "memory":
        return run_threads_test(InMemorySystem(), workers, operations)

    if backend == "file":
        test_dir = prepare_loadtest_dir(BASE_DIR)
        return run_processes_file_test(test_dir, workers, operations)

    raise ValueError(f"Unknown backend: {backend}")


def run_stress_test(
    mode: str,
    worker_steps: list[int],
    operation_steps: list[int],
    max_seconds: float,
) -> list[dict[str, object]]:
    backends = ["memory", "file"] if mode == "both" else [mode]
    rows = []

    for backend in backends:
        stop_backend = False

        for workers in worker_steps:
            if stop_backend:
                break

            for operations in operation_steps:
                report = run_backend_once(backend, workers, operations)
                errors = collect_report_errors(report)
                seconds = float(report["seconds"])
                peak_memory = report_peak_memory(report)

                status = "ok"
                if errors:
                    status = "error"
                elif seconds > max_seconds:
                    status = "slow"

                row = {
                    "backend": backend,
                    "workers": workers,
                    "operations_per_worker": operations,
                    "total_operations": workers * operations,
                    "seconds": seconds,
                    "memory_peak_mb": peak_memory,
                    "status": status,
                    "errors": errors,
                }
                rows.append(row)

                if status != "ok":
                    stop_backend = True
                    break

    return rows


def print_stress_table(rows: list[dict[str, object]]) -> None:
    columns = [
        ("backend", 8),
        ("workers", 7),
        ("ops/w", 8),
        ("total", 8),
        ("sec", 8),
        ("peak_mb", 9),
        ("status", 8),
        ("errors", 30),
    ]

    header = " ".join(name.ljust(width) for name, width in columns)
    print(header)
    print("-" * len(header))

    for row in rows:
        errors = "; ".join(row["errors"]) if row["errors"] else ""
        peak = row["memory_peak_mb"]
        values = {
            "backend": row["backend"],
            "workers": row["workers"],
            "ops/w": row["operations_per_worker"],
            "total": row["total_operations"],
            "sec": row["seconds"],
            "peak_mb": "" if peak is None else round(peak, 4),
            "status": row["status"],
            "errors": errors[:30],
        }
        print(" ".join(str(values[name]).ljust(width) for name, width in columns))


def print_report(report: dict[str, object]) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=4, default=asdict))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("memory", "file", "both"), default="both")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--operations", type=int, default=1000)
    parser.add_argument("--stress", action="store_true")
    parser.add_argument("--stress-workers", default="1,2,4")
    parser.add_argument("--stress-operations", default="100,500,1000,5000")
    parser.add_argument("--max-seconds", type=float, default=30.0)
    args = parser.parse_args()

    if args.stress:
        rows = run_stress_test(
            mode=args.mode,
            worker_steps=parse_int_steps(args.stress_workers),
            operation_steps=parse_int_steps(args.stress_operations),
            max_seconds=args.max_seconds,
        )
        print_stress_table(rows)
        return

    if args.mode in ("memory", "both"):
        print_report(run_threads_test(InMemorySystem(), args.workers, args.operations))

    if args.mode in ("file", "both"):
        test_dir = prepare_loadtest_dir(BASE_DIR)
        print_report(run_processes_file_test(test_dir, args.workers, args.operations))


if __name__ == "__main__":
    main()
