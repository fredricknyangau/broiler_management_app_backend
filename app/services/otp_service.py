import random
import logging
import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)

class OTPService:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def send_otp(self, phone_number: str) -> str:
        """
        Generate and save a 4-digit OTP code to Redis.
        Expiry: 5 minutes (300 seconds).
        """
        # Generate 4-digit code
        code = f"{random.randint(1000, 9999)}"
        
        # Save to Redis
        key = f"otp:{phone_number}"
        await self.redis_client.setex(key, 300, code)
        
        # Ideally, send via SMS provider.
        # For now, we log it or return it for debug.
        logger.info(f"OTP for {phone_number} is {code}")
        
        return code

    async def verify_otp(self, phone_number: str, code: str) -> bool:
        """
        Verify the OTP against the saved code in Redis.
        If matches, delete the key and return True.
        """
        key = f"otp:{phone_number}"
        saved_code = await self.redis_client.get(key)
        
        if not saved_code:
            return False
            
        if saved_code == code:
            # Delete key to prevent reuse
            await self.redis_client.delete(key)
            return True
            
        return False
