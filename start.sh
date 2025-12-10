#!/bin/bash
set -e

# Run migrations (always safe to check)
echo "Running database migrations..."
alembic upgrade head

# Check environment for start mode
if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ]; then
    echo "Starting application in DEVELOPMENT mode (uvicorn)..."
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload --no-server-header
else
    echo "Starting application in PRODUCTION mode (gunicorn)..."
    # Gunicorn with Uvicorn workers
    # Adjust workers based on CPU cores if needed, but 4 is a safe default for now
    exec gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000}
fi
