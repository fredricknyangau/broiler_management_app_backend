from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_db, get_current_admin_user
from app.db.models.user import User
from app.db.models.config import SystemConfig
from uuid import uuid4

class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

@pytest.fixture
def mock_db():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.delete = AsyncMock()
    return mock_session

@pytest.fixture
def mock_admin():
    return User(
        id=uuid4(),
        email="admin@example.com",
        is_superuser=True,
        role="ADMIN",
        is_active=True
    )

@pytest.fixture
def client(mock_db, mock_admin):
    async def override_get_db():
        yield mock_db

    def override_get_current_admin_user():
        return mock_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_config(client, mock_db):
    # Use a plain object instead of MagicMock to avoid nested mocks
    mock_config = MockObj(
        id=uuid4(),
        key="MAINTENANCE_MODE",
        value="false",
        category="system",
        is_encrypted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    mock_default_1 = MockObj(
        id=uuid4(),
        key="REGISTRATION_OPEN",
        value="true",
        category="system",
        is_encrypted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_default_2 = MockObj(
        id=uuid4(),
        key="GLOBAL_BANNER",
        value="",
        category="system",
        is_encrypted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_config, mock_default_1, mock_default_2]
    mock_result.scalars.return_value = mock_scalars
    
    async def mock_execute(stmt, *args, **kwargs):
        return mock_result
        
    mock_db.execute.side_effect = mock_execute
    
    response = client.get("/api/v1/admin/config")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["key"] == "MAINTENANCE_MODE"
