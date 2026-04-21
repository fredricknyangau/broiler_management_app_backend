#!/bin/bash
set -e

# Run migrations (always safe to check)
echo "Running database migrations..."
alembic upgrade head

# Check environment for start mode
if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ]; then
    echo "Starting application in DEVELOPMENT mode (uvicorn)..."
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --reload --no-server-header
else
    echo "Starting application in PRODUCTION mode (gunicorn)..."
    # Gunicorn with Uvicorn workers
    # Preload speeds up worker booting to satisfy Render's healthcheck scanner
    exec gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8080} --preload
fi
