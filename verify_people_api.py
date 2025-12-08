
import requests
import sys

# Constants - Adjust as needed
API_URL = "http://localhost:8000/api/v1"
# Admin credentials (assumed to work based on previous context, otherwise we might need to create one or use existing token logic if available)
# Since I cannot easily log in without a full auth flow interactive script, 
# I will check if there is a way to get a token or if I should mock it.
# Actually, I can try to login first.

USERNAME = "admin@example.com" # Example
PASSWORD = "password" # Example

def login(email, password):
    try:
        response = requests.post(f"{API_URL}/auth/login", data={"username": email, "password": password})
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"Login failed: {response.text}")
            return None
    except Exception as e:
        print(f"Connection error: {e}")
        return None

def verify_people_endpoints(token):
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Supplier
    supplier_data = {
        "name": "Test Supplier",
        "category": "feed",
        "phone_number": "1234567890"
    }
    print("Creating Supplier...")
    resp = requests.post(f"{API_URL}/people/suppliers", json=supplier_data, headers=headers)
    if resp.status_code != 200:
        print(f"Error creating supplier: {resp.text}")
    else:
        supplier_id = resp.json()["id"]
        print(f"Supplier created: {supplier_id}")
    
    # 2. Get Suppliers
    print("Fetching Suppliers...")
    resp = requests.get(f"{API_URL}/people/suppliers", headers=headers)
    if resp.status_code == 200:
        print(f"Suppliers found: {len(resp.json())}")
    else:
        print(f"Error fetching suppliers: {resp.text}")

    # 3. Create Customer
    customer_data = {
        "name": "Test Customer",
        "customer_type": "retail",
        "email": "cust@example.com"
    }
    print("Creating Customer...")
    resp = requests.post(f"{API_URL}/people/customers", json=customer_data, headers=headers)
    if resp.status_code != 200:
        print(f"Error creating customer: {resp.text}")
    else:
        print(f"Customer created: {resp.json()['id']}")

    # 4. Create Employee
    employee_data = {
        "name": "Test Employee",
        "role": "worker",
        "salary": 15000
    }
    print("Creating Employee...")
    resp = requests.post(f"{API_URL}/people/employees", json=employee_data, headers=headers)
    if resp.status_code != 200:
        print(f"Error creating employee: {resp.text}")
    else:
        print(f"Employee created: {resp.json()['id']}")

if __name__ == "__main__":
    # We need a valid user to test this.
    # checking if verifying_api.py exists or similar helper
    print("Starting verification...")
    # I'll rely on the existing 'verify_api.py' if it exists or just run this simple check if I can get a token.
    # For now, let's just try to list endpoints from openapi.json to verify router mounting without auth 
    # (or Assume I can use a test user)
    
    try:
        resp = requests.get("http://localhost:8000/openapi.json")
        if resp.status_code == 200:
            schema = resp.json()
            paths = schema.get("paths", {})
            people_paths = [p for p in paths if "/people" in p]
            print(f"Found {len(people_paths)} people endpoints in OpenAPI schema.")
            for p in people_paths:
                print(f" - {p}")
        else:
            print("Could not fetch OpenAPI schema")
    except Exception as e:
        print(f"Error connecting to API: {e}")
