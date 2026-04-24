import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.main import app
from app.api.deps import get_db
from app.db.base import Base
from app.config import settings
from app.core.security import create_access_token
import uuid
from app.workers.celery_app import celery_app


@pytest.fixture(scope="session", autouse=True)
def configure_celery():
    celery_app.conf.update(task_always_eager=True)
    yield


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine):
    connection = await db_engine.connect()
    transaction = await connection.begin()
    
    SessionLocal = async_sessionmaker(
        bind=connection, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    session = SessionLocal()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def test_user(db_session):
    from app.db.models.user import User
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"test_{user_id.hex[:6]}@example.com",
        hashed_password="fakehashed",
        full_name="Test User",
        is_active=True,
        role="FARMER"
    )
    db_session.add(user)
    await db_session.flush()
    return user

@pytest_asyncio.fixture
async def auth_headers(test_user):
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def test_user_2(db_session):
    from app.db.models.user import User
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"test2_{user_id.hex[:6]}@example.com",
        hashed_password="fakehashed",
        full_name="Test User 2",
        is_active=True,
        role="FARMER"
    )
    db_session.add(user)
    await db_session.flush()
    return user

@pytest_asyncio.fixture
async def auth_headers_2(test_user_2):
    token = create_access_token(data={"sub": str(test_user_2.id)})
    return {"Authorization": f"Bearer {token}"}
