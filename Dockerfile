# Multi-stage build for smaller and more secure image

# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

# Copy and install dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only main --no-interaction --no-ansi

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Create a non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Install run-time dependencies (libpq for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Make start script executable (if not already)
RUN chmod +x start.sh

# Command to run the application
CMD ["./start.sh"]
