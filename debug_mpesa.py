import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from app.config import settings
from app.services.mpesa_service import mpesa_service
from datetime import datetime
import traceback
import requests

print("--- M-Pesa Debug Script (httpbin) ---")
# Use httpbin which accepts POST and returns 200
DUMMY_CALLBACK_URL = "https://httpbin.org/post" 
# Manual override
settings.MPESA_CALLBACK_URL = DUMMY_CALLBACK_URL
print(f"Overridden Callback URL: {settings.MPESA_CALLBACK_URL}")

TEST_PHONE = "254708374149"
TEST_AMOUNT = 1

try:
    print(f"\nInitiating STK Push to {TEST_PHONE}...")
    reference = f"TEST-{int(datetime.now().timestamp())}"
    
    response = mpesa_service.initiate_stk_push(
        phone=TEST_PHONE,
        amount=TEST_AMOUNT,
        reference=reference
    )
    print(f"Success! Response: {response}")
except Exception as e:
    print("\nFAILED to initiate STK Push:")
    traceback.print_exc()
    if hasattr(e, 'response') and e.response:
        print(f"Response Body: {e.response.text}")
