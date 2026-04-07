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
        Included: Rate limiting to prevent SMS bombing (max 3 reqs per 15 min).
        """
        rate_limit_key = f"rate_limit:otp:{phone_number}"
        attempts = await self.redis_client.get(rate_limit_key)
        
        if attempts and int(attempts) >= 3:
            logger.warning(f"OTP rate limit exceeded for {phone_number}")
            raise ValueError("Too many OTP requests. Please try again in 15 minutes.")
            
        # Generate 4-digit code
        code = f"{random.randint(1000, 9999)}"
        
        # Save to Redis
        key = f"otp:{phone_number}"
        await self.redis_client.setex(key, 300, code)
        
        # Update rate limits
        if not attempts:
            await self.redis_client.setex(rate_limit_key, 900, 1)  # 15 minutes window
        else:
            await self.redis_client.incr(rate_limit_key)
        
        # Avoid leaking OTPs to centralized logs in production.
        if settings.DEBUG:
            logger.info(f"[DEBUG] OTP for {phone_number} is {code}")
        else:
            logger.info(f"OTP generated and SMS queue hit for {phone_number}")
        
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
