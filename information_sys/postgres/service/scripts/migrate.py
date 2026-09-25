from pathlib import Path
import sys


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from app.db import write_engine


MIGRATIONS = APP_ROOT / "migrations"


def main() -> None:
    files = sorted(MIGRATIONS.glob("*.sql"))
    if not files:
        raise SystemExit("No migrations found")

    with write_engine.begin() as connection:
        for path in files:
            print(f"Applying {path.name}")
            connection.exec_driver_sql(path.read_text(encoding="utf-8"))
    print("Migrations completed")


if __name__ == "__main__":
    main()
