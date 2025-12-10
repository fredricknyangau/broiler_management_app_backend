# Broiler Farm Management System - Backend API

FastAPI-based backend for the Broiler Farm Management System.

## Tech Stack

- **Framework**: FastAPI (Python 3.12)
- **Database**: PostgreSQL 16 (Async via `asyncpg`, ORM: SQLAlchemy 2.0)
- **Migrations**: Alembic
- **Task Queue**: Celery with Redis
- **Containerization**: Docker & Docker Compose
- **Dependency Management**: Poetry
- **Security**: OAuth2, Strict headers, Non-root containers

## Local Development Setup

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL (if running locally without Docker)
- Redis (if running locally without Docker)

### 1. Clone & Configure

```bash
git clone <repository_url>
cd backend
cp .env.production.example .env
# Edit .env and set DEBUG=True for development
```

### 2. Run with Docker Compose (Recommended)

This starts the Database, Redis, API, and Celery workers.

```bash
docker-compose up -d --build
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### 3. Run Manually (Alternative)

If you prefer running Python directly:

```bash
# Install dependencies
pip install poetry
poetry install

# Start dependencies
docker-compose up -d postgres redis

# Run migrations
poetry run alembic upgrade head

# Start API
poetry run uvicorn app.main:app --reload
```

## Configuration

The application is configured via environment variables (in `.env`).

| Variable               | Description                                   | Default/Example                               |
| ---------------------- | --------------------------------------------- | --------------------------------------------- |
| `DEBUG`                | Toggle debug mode (stack traces, auto-reload) | `False` (Prod), `True` (Dev)                  |
| `SECRET_KEY`           | **CRITICAL**: Used for signing JWTs           | Use `python3 scripts/generate_secret.py`      |
| `DATABASE_URL`         | Postgres Connection String                    | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL`            | Redis Connection String                       | `redis://host:6379/0`                         |
| `BACKEND_CORS_ORIGINS` | Allowed CORS origins                          | `["http://localhost:5173"]`                   |

## Security Features

### 1. Docker Security

- **Multi-stage Build**: The Dockerfile uses a multi-stage process to exclude build tools from the final image.
- **Non-root User**: The application runs as `appuser` inside the container for enhanced security.

### 2. Production Ready

- **Process Manager**: Uses `gunicorn` with `uvicorn` workers in production (`DEBUG=False`).
- **Headers**: Middleware enforces strict security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`).

### 3. Secrets

- Never use the default secret key in production.
- Run the helper script to generate a secure key:
  ```bash
  python3 scripts/generate_secret.py
  ```

## Deployment

### Render / Cloud Deployment

1. **Build Command**: The `Dockerfile` is self-contained.
2. **Start Command**: `./start.sh`
   - This script automatically detects `DEBUG` mode.
   - Ensure `DEBUG=False` in your cloud environment variables.
3. **Health Check**: `/health` endpoint is available.

### Manual Production Run

```bash
# Build image
docker build -t broiler-backend .

# Run container (Example)
docker run -d \
  -p 8000:8000 \
  -e DEBUG=False \
  -e SECRET_KEY=<your-secure-key> \
  -e DATABASE_URL=<prod-db-url> \
  --name broiler-backend \
  broiler-backend
```
