"""Open several PostgreSQL sessions to demonstrate the connection limit."""

import os
import sys
import time

import psycopg


count = int(sys.argv[1]) if len(sys.argv) > 1 else 25
seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 60
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
connections = []

for number in range(count):
    try:
        connections.append(psycopg.connect(url, connect_timeout=2))
        print(f"Connection {number + 1}: opened")
    except Exception as exc:
        print(f"Connection {number + 1}: rejected ({exc})")

print(f"Holding {len(connections)} connections for {seconds} seconds...")
time.sleep(seconds)

for connection in connections:
    connection.close()

