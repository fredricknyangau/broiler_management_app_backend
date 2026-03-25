import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_db
from app.db.models.user import User

# Mock DB Session
mock_session = AsyncMock()

async def override_get_db():
    yield mock_session

# Override the DB dependency
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.mark.asyncio
@patch("app.api.v1.auth.OTPService.send_otp", new_callable=AsyncMock)
async def test_send_otp(mock_send_otp):
    # Setup
    mock_send_otp.return_value = "1234"
    
    payload = {"phone_number": "+254712345678"}
    response = client.post("/api/v1/auth/send-otp", json=payload)
    
    # Assertions
    assert response.status_code == 200
    assert response.json()["message"] == "OTP sent successfully"
    assert response.json()["code"] == "1234"
    mock_send_otp.assert_called_once_with("+254712345678")


@pytest.mark.asyncio
@patch("app.api.v1.auth.OTPService.verify_otp", new_callable=AsyncMock)
@patch("app.api.v1.auth.UserService.get_or_create_user_by_phone", new_callable=AsyncMock)
async def test_verify_otp_success(mock_get_or_create, mock_verify_otp):
    # Setup
    mock_verify_otp.return_value = True
    
    # Create fake user
    import uuid
    mock_user = User(
        id=uuid.uuid4(), 
        phone_number="+254712345678",
        is_active=True,
        role="FARMER"
    )
    mock_get_or_create.return_value = (mock_user, True)
    
    payload = {"phone_number": "+254712345678", "code": "1234"}
    response = client.post("/api/v1/auth/verify-otp", json=payload)
    
    # Assertions
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    assert response.json()["is_new_user"] is True


@pytest.mark.asyncio
@patch("app.api.v1.auth.OTPService.verify_otp", new_callable=AsyncMock)
async def test_verify_otp_invalid(mock_verify_otp):
    # Setup
    mock_verify_otp.return_value = False
    
    payload = {"phone_number": "+254712345678", "code": "9999"}
    response = client.post("/api/v1/auth/verify-otp", json=payload)
    
    # Assertions
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired OTP code"
