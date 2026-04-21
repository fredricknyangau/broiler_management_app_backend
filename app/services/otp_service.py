import asyncio
import logging
import random

import africastalking
import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class OTPDeliveryError(Exception):
    """Raised when an OTP cannot be delivered to the SMS provider."""


class OTPService:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

        # Initialize Africa's Talking
        self.sms = None
        if (
            settings.AFRICASTALKING_USERNAME
            and settings.AFRICASTALKING_API_KEY
            and settings.AFRICASTALKING_API_KEY != "place_holder"
        ):
            africastalking.initialize(
                settings.AFRICASTALKING_USERNAME, settings.AFRICASTALKING_API_KEY
            )
            self.sms = africastalking.SMS
        else:
            logger.warning("Africa's Talking is not properly configured.")

    def _normalize_phone(self, phone_number: str) -> str:
        """
        Normalize phone number to E.164 format required by Africa's Talking.
        Handles Kenyan numbers:  07XX → +254XX,  254XX → +254XX,  +254XX → +254XX
        """
        phone = phone_number.strip().replace(" ", "").replace("-", "")
        if phone.startswith("0"):
            phone = "+254" + phone[1:]
        elif phone.startswith("254") and not phone.startswith("+"):
            phone = "+" + phone
        return phone

    async def _send_sms_async(self, phone_number: str, message: str) -> None:
        """Helper to call synchronous Africa's Talking API without blocking the event loop."""
        if not self.sms:
            error_message = (
                "Cannot send SMS: Africa's Talking SMS client not initialized. "
                "Check AFRICASTALKING_USERNAME and AFRICASTALKING_API_KEY env vars."
            )
            logger.error(error_message)
            raise OTPDeliveryError(error_message)

        def _send():
            try:
                response = self.sms.send(message, [phone_number])
                logger.info(f"Africa's Talking API Response: {response}")
                # Inspect per-recipient delivery status for early failure detection
                recipients = response.get("SMSMessageData", {}).get("Recipients", [])
                for r in recipients:
                    if r.get("status") != "Success":
                        raise OTPDeliveryError(
                            f"SMS delivery failed for {r.get('number')}: "
                            f"{r.get('status')} (code: {r.get('statusCode')})"
                        )
                    logger.info(
                        f"SMS delivered to {r.get('number')} (cost: {r.get('cost')})"
                    )
            except Exception as e:
                logger.error(f"Africa's Talking SDK Error: {e}", exc_info=True)
                if isinstance(e, OTPDeliveryError):
                    raise
                raise OTPDeliveryError(str(e)) from e

        await asyncio.to_thread(_send)

    async def send_otp(self, phone_number: str) -> str:
        """
        Generate and save a 4-digit OTP code to Redis.
        Expiry: 5 minutes (300 seconds).
        Included: Rate limiting to prevent SMS bombing (max 3 reqs per 15 min).
        """
        # Normalize to E.164 before anything else
        phone_number = self._normalize_phone(phone_number)
        logger.info(f"Sending OTP to normalized number: {phone_number}")
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
        message = f"Your KukuFiti verification code is {code}. It expires in 5 minutes."

        if settings.DEBUG:
            logger.info(f"[DEBUG] OTP for {phone_number} is {code}")
        else:
            logger.info(f"OTP generated and SMS queue hit for {phone_number}")

        # Send SMS using AfricasTalking
        await self._send_sms_async(phone_number, message)

        return code

    async def verify_otp(self, phone_number: str, code: str) -> bool:
        """
        Verify the OTP against the saved code in Redis.
        If matches, delete the key and return True.
        """
        phone_number = self._normalize_phone(phone_number)
        key = f"otp:{phone_number}"
        saved_code = await self.redis_client.get(key)

        if not saved_code:
            return False

        if saved_code == code:
            # Delete key to prevent reuse
            await self.redis_client.delete(key)
            return True

        return False
