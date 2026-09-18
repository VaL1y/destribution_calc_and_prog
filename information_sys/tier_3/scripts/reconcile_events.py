"""Copy missing append-only inventory events from one primary to another."""

import argparse
import os

import psycopg


def connect(host: str) -> psycopg.Connection:
    return psycopg.connect(
        host=host,
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "warehouse"),
        user=os.getenv("POSTGRES_USER", "warehouse"),
        password=os.getenv("POSTGRES_PASSWORD", "warehouse"),
        connect_timeout=3,
        target_session_attrs="read-write",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge missing inventory_events into the selected primary"
    )
    parser.add_argument("--source-host", required=True)
    parser.add_argument("--target-host", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with connect(args.source_host) as source:
        with source.cursor() as cursor:
            cursor.execute(
                """
                SELECT event_id, source_node, product_id, delta, note, created_at
                FROM warehouse.inventory_events
                ORDER BY created_at, event_id
                """
            )
            events = cursor.fetchall()

    if args.dry_run:
        print(f"source_events={len(events)} target={args.target_host} dry_run=true")
        return

    inserted = 0
    with connect(args.target_host) as target:
        with target.cursor() as cursor:
            for event in events:
                cursor.execute(
                    """
                    INSERT INTO warehouse.inventory_events
                        (event_id, source_node, product_id, delta, note, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    event,
                )
                inserted += cursor.rowcount

    print(
        f"source_events={len(events)} inserted={inserted} "
        f"already_present={len(events) - inserted} target={args.target_host}"
    )


if __name__ == "__main__":
    main()

