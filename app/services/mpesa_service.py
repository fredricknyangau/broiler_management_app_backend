import requests
import base64
from datetime import datetime
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# You would technically put these in settings
MPESA_CONSUMER_KEY = "PLACEHOLDER_KEY"
MPESA_CONSUMER_SECRET = "PLACEHOLDER_SECRET"
MPESA_PASSKEY = "PLACEHOLDER_PASSKEY"
MPESA_SHORTCODE = "174379" # Test shortcode
MPESA_CALLBACK_URL = f"{settings.API_V1_PREFIX}/billing/mpesa/callback" 

class MpesaService:
    def __init__(self):
        self.auth_token = None

    def _get_auth_token(self):
        auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        try:
            logger.info(f"Attempting M-Pesa Auth: {auth_url}")
            logger.info(f"Key: {settings.MPESA_CONSUMER_KEY[:5]}... | Secret: {settings.MPESA_CONSUMER_SECRET[:5]}...")
            response = requests.get(
                auth_url, 
                auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET)
            )
            response.raise_for_status()
            return response.json().get('access_token')
        except Exception as e:
            logger.error(f"Error fetching auth token: {e}")
            raise e

    def initiate_stk_push(self, phone: str, amount: int, reference: str):
        logger.info(f"Initiating STK Push to {phone} for {amount} KES. Ref: {reference}")
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
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
            "TransactionDesc": "Subscription Payment"
        }
        
        headers = { "Authorization": f"Bearer {self._get_auth_token()}" }
        
        try:
            logger.info(f"Sending STK Push Payload: {payload}")
            response = requests.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", 
                json=payload, 
                headers=headers
            )
            response.raise_for_status()
            logger.info(f"STK Push Response: {response.json()}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"STK Push failed: {e}")
            if e.response is not None:
                error_body = e.response.text
                logger.error(f"Response body: {error_body}")
                # Raise a new exception with the response body so top-level can see it
                raise Exception(f"M-Pesa API Error: {error_body}")
            raise e
        except Exception as e:
            logger.error(f"STK Push failed: {e}")
            raise e

mpesa_service = MpesaService()
