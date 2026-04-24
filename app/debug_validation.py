from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.config import SystemConfigResponse

data = {
    "id": uuid4(),
    "key": "TEST",
    "value": "VALUE",
    "category": "system",
    "is_encrypted": False,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
}

try:
    obj = SystemConfigResponse.model_validate(data)
    print("VALID")
except ValidationError as e:
    print(e.json())
