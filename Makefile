# Makefile
.PHONY: help build up down logs shell db-shell migrate test

help:
	@echo "Broiler Farm Management System - Make Commands"
	@echo "=============================================="
	@echo "build       - Build Docker images"
	@echo "up          - Start all services"
	@echo "down        - Stop all services"
	@echo "logs        - View logs from all services"
	@echo "shell       - Open shell in API container"
	@echo "db-shell    - Open PostgreSQL shell"
	@echo "migrate     - Run database migrations"
	@echo "test        - Run tests"
	@echo "lint        - Run code linting"
	@echo "format      - Format code with black and isort"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

shell:
	docker-compose exec api /bin/bash

db-shell:
	docker-compose exec postgres psql -U broiler_user -d broiler_farm_db

migrate:
	docker-compose exec api alembic upgrade head

test:
	docker-compose exec api pytest

lint:
	docker-compose exec api pylint app

format:
	docker-compose exec api black app
	docker-compose exec api isort app