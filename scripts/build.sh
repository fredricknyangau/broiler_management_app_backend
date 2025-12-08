#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install poetry
pip install -U pip
pip install poetry

# Install dependencies
poetry config virtualenvs.create false
poetry install --no-interaction --no-ansi
