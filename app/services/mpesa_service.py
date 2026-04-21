import base64
from datetime import datetime, timezone

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class MpesaService:
    """
    Thin wrapper around Safaricom Daraja API.

    All credentials are sourced exclusively from ``settings`` (pydantic-settings → .env).
    No hardcoded placeholder values exist here; the app will refuse to start if the
    required env-vars are missing (enforced via pydantic-settings validation).
    """

    async def _get_auth_token(self) -> str:
        """Fetch a short-lived OAuth2 bearer token from Safaricom."""
        auth_url = (
            f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
        )
        logger.info("Fetching M-Pesa OAuth token")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                auth_url,
                auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
            )
            response.raise_for_status()
            token = response.json().get("access_token")
            if not token:
                raise ValueError("M-Pesa auth response missing access_token")
            return token

    async def initiate_stk_push(self, phone: str, amount: int, reference: str) -> dict:
        """
        Initiate an M-Pesa STK Push (Lipa na M-Pesa Online).

        Args:
            phone:     Kenyan phone number in 254XXXXXXXXX format.
            amount:    Amount in KES (integer).
            reference: Unique account reference (e.g. "SALE-<uuid>").

        Returns:
            Safaricom response dict containing CheckoutRequestID.

        Raises:
            Exception: On API error, with the upstream response body included.
        """
        logger.info(
            "Initiating STK Push",
            extra={
                "phone": phone[-4:].zfill(len(phone)),
                "amount": amount,
                "ref": reference,
            },
        )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        password_str = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": reference,
            "TransactionDesc": "KukuFiti Payment",
        }

        try:
            token = await self._get_auth_token()
            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                logger.info("STK Push accepted by Safaricom", extra={"ref": reference})
                return response.json()

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error("STK Push rejected", extra={"body": error_body})
            raise Exception(f"M-Pesa API Error: {error_body}") from e
        except Exception as e:
            logger.error("STK Push failed unexpectedly: %s", e)
            raise

    async def query_stk_status(self, checkout_request_id: str) -> dict:
        """
        Query the status of an STK Push transaction directly from Safaricom.

        This is used for CALLBACK VERIFICATION: after receiving a callback, call
        this method to re-confirm the transaction status server-side before
        marking any subscription or sale as paid. This prevents fake callbacks.

        Args:
            checkout_request_id: The CheckoutRequestID returned by initiate_stk_push.

        Returns:
            Safaricom query response dict. ResultCode == "0" means success.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        password_str = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        try:
            token = await self._get_auth_token()
            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{settings.MPESA_BASE_URL}/mpesa/stkpushquery/v1/query",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()
                logger.info(
                    "STK Query result",
                    extra={
                        "checkout_id": checkout_request_id,
                        "code": result.get("ResultCode"),
                    },
                )
                return result

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error("STK Query failed", extra={"body": error_body})
            raise Exception(f"M-Pesa Query Error: {error_body}") from e
        except Exception as e:
            logger.error("STK Query failed unexpectedly: %s", e)
            raise


mpesa_service = MpesaService()
