
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.security import create_access_token
from app.db.models.user import User
from app.db.models.flock import Flock
from uuid import uuid4
from datetime import date


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.types import JSON
import sqlalchemy.types as types

# Patch JSONB for SQLite
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, 'sqlite')
def compile_jsonb(type_, compiler, **kw):
    return "JSON"

@compiles(ARRAY, 'sqlite')
def compile_array(type_, compiler, **kw):
    return "JSON"

# Setup Test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Patch execute to ignore SET LOCAL
    original_execute = session.execute
    def execute_wrapper(statement, *args, **kwargs):
        if isinstance(statement, str) and statement.strip().startswith("SET LOCAL"):
            return None
        # Also catch TextClause
        if hasattr(statement, "text") and str(statement).strip().startswith("SET LOCAL"):
            return None
        # Also catch compiled objects if possible, but usually it's text for SET LOCAL
        return original_execute(statement, *args, **kwargs)
    
    session.execute = execute_wrapper
    
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db):
    from app.api.deps import get_db
    # Mock evaluate_alerts_task.delay in daily_checks module
    from app.workers import tasks
    from app.api.v1 import daily_checks
    
    # We need to patch the reference in daily_checks module
    original_evaluate_alerts_task = daily_checks.evaluate_alerts_task
    daily_checks.evaluate_alerts_task = type('obj', (object,), {'delay': lambda *args, **kwargs: None})

    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    # Cleanup
    daily_checks.evaluate_alerts_task = original_evaluate_alerts_task

def test_daily_check_isolation_vulnerability(client: TestClient, db: Session):
    # 1. Setup: Create two users
    user_a_email = f"user_a_{uuid4()}@example.com"
    user_b_email = f"user_b_{uuid4()}@example.com"
    
    user_a = User(email=user_a_email, hashed_password="hashed_password", is_active=True)
    user_b = User(email=user_b_email, hashed_password="hashed_password", is_active=True)
    db.add(user_a)
    db.add(user_b)
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)
    
    # 2. Create Flock for User A
    flock_a = Flock(
        farmer_id=user_a.id,
        name="User A Flock",
        start_date=date.today(),
        initial_count=100,
        status="active"
    )
    db.add(flock_a)
    db.commit()
    db.refresh(flock_a)
    
    # 3. Authenticate as User B
    token_b = create_access_token(data={"sub": str(user_b.id)})
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # 4. Attempt to add a daily check to Flock A using User B's token
    payload = {
        "flock_id": str(flock_a.id),
        "check_date": str(date.today()),
        "events": []
    }
    
    response = client.post("/api/v1/daily-checks", json=payload, headers=headers_b)
    
    # 5. Assert EXPECTED FAILURE (Vulnerability Check)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 201:
        pytest.fail("VULNERABILITY CONFIRMED: User B was able to add a check to User A's flock.")
    elif response.status_code == 404:
        print("Secure: Resource not found for unauthorized user.")
    else:
        print(f"Unexpected status: {response.status_code}")

