"""Tests for config validation"""
import os
import sys

import pytest
from pydantic import ValidationError


def test_secret_key_validation():
    """Test that SECRET_KEY cannot be the default placeholder."""
    # Store original env vars
    original_secret = os.getenv('SECRET_KEY')

    try:
        # Set invalid secret
        os.environ['SECRET_KEY'] = 'change-me-in-production'

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            from app.config import Settings
            Settings()

        assert 'SECRET_KEY' in str(exc_info.value)
    finally:
        # Restore
        if original_secret:
            os.environ['SECRET_KEY'] = original_secret
        else:
            os.environ.pop('SECRET_KEY', None)


def test_secret_key_length():
    """Test that SECRET_KEY must be at least 32 characters."""
    original_secret = os.getenv('SECRET_KEY')

    try:
        # Set short secret
        os.environ['SECRET_KEY'] = 'short'

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            # Force reload of config module
            if 'app.config' in sys.modules:
                del sys.modules['app.config']
            from app.config import Settings
            Settings()

        assert '32 characters' in str(exc_info.value)
    finally:
        if original_secret:
            os.environ['SECRET_KEY'] = original_secret
        else:
            os.environ.pop('SECRET_KEY', None)


def test_database_url_validation():
    """Test that DATABASE_URL is required."""
    original_db = os.getenv('DATABASE_URL')

    try:
        # Set to empty string to trigger validator (it has a default, so pop doesn't work)
        os.environ['DATABASE_URL'] = ''

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            if 'app.config' in sys.modules:
                del sys.modules['app.config']
            from app.config import Settings
            Settings()

        assert 'DATABASE_URL' in str(exc_info.value)
    finally:
        if original_db:
            os.environ['DATABASE_URL'] = original_db
        else:
            os.environ.pop('DATABASE_URL', None)


def test_valid_config():
    """Test that valid config loads without errors."""
    # Set required env vars
    os.environ['SECRET_KEY'] = 'a' * 64  # Valid 64-char key
    os.environ['DATABASE_URL'] = 'postgresql+asyncpg://user:pass@localhost/db'

    try:
        if 'app.config' in sys.modules:
            del sys.modules['app.config']
        from app.config import Settings
        config = Settings()

        assert config.SECRET_KEY == 'a' * 64
        assert config.DATABASE_URL == 'postgresql+asyncpg://user:pass@localhost/db'
    finally:
        pass
