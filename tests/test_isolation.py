import pytest
import pytest_asyncio
from httpx import AsyncClient
import uuid

@pytest.mark.asyncio
async def test_flock_isolation(client, test_user, auth_headers, test_user_2, auth_headers_2):
    # client is already a yielded value from conftest
    # 1. User 1 creates a flock
    flock_data = {
        "name": "User 1 Flock",
        "breed": "Ross 308",
        "start_date": "2024-01-01",
        "initial_count": 10,  # Small count for starter plan
        "cost_per_bird": 50.0
    }
    response = await client.post("/api/v1/flocks/", json=flock_data, headers=auth_headers)
    assert response.status_code in [200, 201]
    flock_id = response.json()["id"]

    # 2. User 2 tries to read User 1's flock
    response = await client.get(f"/api/v1/flocks/{flock_id}", headers=auth_headers_2)
    assert response.status_code == 404

    # 3. User 2 tries to list flocks, should not see User 1's flock
    response = await client.get("/api/v1/flocks/", headers=auth_headers_2)
    assert response.status_code == 200
    flocks = response.json()
    assert all(f["id"] != flock_id for f in flocks)

@pytest.mark.asyncio
async def test_create_flock_triggers_expenditure(client, test_user, auth_headers, db_session):
    from app.db.models.finance import Expenditure
    from sqlalchemy import select

    flock_data = {
        "name": "Finance Test Flock",
        "breed": "Cobb 500",
        "start_date": "2024-02-01",
        "initial_count": 10,
        "cost_per_bird": 60.0
    }
    response = await client.post("/api/v1/flocks/", json=flock_data, headers=auth_headers)
    assert response.status_code in [200, 201]
    flock_id = response.json()["id"]

    # Check if expenditure was created
    result = await db_session.execute(
        select(Expenditure).filter(Expenditure.flock_id == uuid.UUID(flock_id))
    )
    expenditure = result.scalars().first()
    assert expenditure is not None
    assert float(expenditure.amount) == 10 * 60.0
    assert expenditure.category == "chick_acquisition"
