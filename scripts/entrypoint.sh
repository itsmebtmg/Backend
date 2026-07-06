#!/usr/bin/env sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting Solyra API..."
exec fastapi run app/main.py --host 0.0.0.0 --port 8000
