FROM python:3.12-slim

WORKDIR /app

COPY information_sys/tier_1 /app

CMD ["python", "main.py", "--stress", "--mode", "both", "--stress-workers", "4,8", "--stress-operations", "1000,5000,10000,20000", "--max-seconds", "15"]
