
from fastapi.testclient import TestClient
from app.main import app
from app.api import deps
from app.db.models.user import User
import uuid

# Mock the dependency to bypass auth and return a fake user
# We need to find valid user ID from DB or just create a mock object if the code doesn't check DB existence deeply
# specific to the endpoint logic

# However, the endpoint query filters by user_id:
# db.query(Supplier).filter(Supplier.user_id == current_user.id)...

from app.db.session import SessionLocal

# Fetch a real user from DB
db = SessionLocal()
try:
    user = db.query(User).first()
    if not user:
        print("No users found in database! Creating one for testing...")
        # Optional: create user
        mock_user_id = uuid.uuid4()
    else:
        print(f"Using existing user: {user.email} (ID: {user.id})")
        mock_user_id = user.id
finally:
    db.close()

class MockUser:
    id = mock_user_id
    is_active = True
    is_superuser = True

def override_get_current_user():
    return MockUser()

app.dependency_overrides[deps.get_current_user] = override_get_current_user

client = TestClient(app)


print("Attemping to create supplier...")
try:
    supplier_data = {
        "name": "Test Supplier",
        "category": "feed",
        "notes": "Created by debug script"
    }
    create_resp = client.post("/api/v1/people/suppliers", json=supplier_data)
    print(f"Create Status: {create_resp.status_code}")
    print(f"Create Response: {create_resp.content}")

    print("Attemping to fetch suppliers...")
    response = client.get("/api/v1/people/suppliers")
    print(f"Read Status: {response.status_code}")
    print(f"Read Response: {response.content}")
except Exception as e:
    print(f"Crash detected: {e}")
    import traceback
    traceback.print_exc()
