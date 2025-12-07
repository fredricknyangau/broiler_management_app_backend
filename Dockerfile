# Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies (including gcc for building some python packages if needed)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Install poetry and dependencies
# We install poetry, then export requirements.txt to install via pip for slimmer image
# Or just use pip if poetry is too heavy, but let's stick to standard practice
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-root --only main --no-interaction --no-ansi

# Copy application code
COPY . .

# Expose port (Render sets $PORT env var, but good to document)
EXPOSE 8000

# Command to run the application
# Use the $PORT environment variable supplied by Render
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
