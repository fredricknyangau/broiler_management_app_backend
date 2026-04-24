from datetime import datetime
from uuid import uuid4

from app.db.models.config import SystemConfig
from app.schemas.config import SystemConfigResponse


def debug_validation():
    config_obj = SystemConfig(
        id=uuid4(),
        key="MAINTENANCE_MODE",
        value="false",
        category="system",
        is_encrypted=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    print(f"Config Object: {config_obj}")
    try:
        response = SystemConfigResponse.from_orm(config_obj)
        print(f"Validated Response: {response}")
    except Exception as e:
        print(f"Validation Error: {e}")


if __name__ == "__main__":
    debug_validation()
