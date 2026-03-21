import os
from app.config import settings

print("DATABASE_URL from settings:", settings.DATABASE_URL)
print("ASYNC_DATABASE_URL from settings:", settings.ASYNC_DATABASE_URL)
print("Environment DATABASE_URL:", os.environ.get("DATABASE_URL"))
