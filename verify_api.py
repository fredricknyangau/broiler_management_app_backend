import requests
import uuid
from datetime import date

BASE_URL = "http://localhost:8000/api/v1"
# Assuming default credentials or I need to register one.
# For now, I'll attempt to use the existing user if I can login, or register new.

EMAIL = f"test_{uuid.uuid4()}@example.com"
PASSWORD = "password123"

def login_or_register():
    session = requests.Session()
    # Try login
    login_payload = {"email": EMAIL, "password": PASSWORD}
    res = session.post(f"{BASE_URL}/auth/login/", json=login_payload)
    
    if res.status_code == 200:
        token = res.json()["access_token"]
        print("Logged in successfully.")
        return token
    
    # Register
    reg_payload = {"email": EMAIL, "password": PASSWORD, "full_name": "Test User", "phone_number": "+254700000000"}
    res = session.post(f"{BASE_URL}/auth/register/", json=reg_payload)
    if res.status_code in [200, 201]:
        print("Registered successfully. Logging in...")
        return login_or_register()
    
    print(f"Login/Register failed: {res.text}")
    return None

def run_test():
    token = login_or_register()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create Flock
    flock_id = str(uuid.uuid4())
    flock_payload = {
        "name": f"Test Flock {flock_id[:8]}",
        "initial_count": 1000,
        "start_date": str(date.today()),
        "breed": "Cob 500",
        "status": "active"
    }
    
    # Check if flock creation endpoint is POST /flocks
    # Based on flocks.py: @router.post("/", ...)
    
    print("Creating flock...")
    res = requests.post(f"{BASE_URL}/flocks/", json=flock_payload, headers=headers)
    if res.status_code not in [200, 201]:
        print(f"Failed to create flock: {res.text}")
        return
    
    flock = res.json()
    flock_id = flock['id']
    print(f"Flock created: {flock_id}")

    # 2. Add Mortality via Daily Check
    check_event_id = str(uuid.uuid4())
    payload = {
        "flock_id": flock_id,
        "check_date": str(date.today()),
        "events": [
            {
                "type": "mortality",
                "data": {
                    "event_id": check_event_id,
                    "count": 5,
                    "cause": "Test Cause",
                    "notes": "Testing persistence"
                }
            }
        ],
        # Observations (required fields?)
        "temperature_celsius": 25.0,
        "humidity_percent": 60.0,
        "chick_behavior": "normal",
        "feed_level": "adequate",
        "water_level": "adequate",
        "litter_condition": "dry"
    }

    print("Submitting daily check...")
    res = requests.post(f"{BASE_URL}/daily-checks", json=payload, headers=headers)
    if res.status_code not in [200, 201]:
        print(f"Failed to submit daily check: {res.text}")
        return
    
    print("Daily check submitted.")

    # 3. Retrieve Mortality Events
    print("Retrieving mortality events...")
    res = requests.get(f"{BASE_URL}/events/mortality?flock_id={flock_id}", headers=headers)
    
    if res.status_code != 200:
        print(f"Failed to retrieve events: {res.text}")
        return
    
    events = res.json()
    print(f"Retrieved {len(events)} mortality events.")
    
    found = False
    for e in events:
        if e['count'] == 5 and e['cause'] == "Test Cause":
            found = True
            print("SUCCESS: Record found!")
            break
            
    if not found:
        print("FAILURE: Record NOT found in response.")
        print("Response:", events)

    # 4. Determine Update Persistence (Reduce Initial Count)
    print("Updating flock initial count...")
    new_count = 950
    update_payload = {"initial_count": new_count}
    res = requests.put(f"{BASE_URL}/flocks/{flock_id}", json=update_payload, headers=headers)
    
    if res.status_code != 200:
        print(f"Failed to update flock: {res.text}")
        return

    # Verify update
    res = requests.get(f"{BASE_URL}/flocks/{flock_id}", headers=headers)
    target_flock = res.json()
    if target_flock['initial_count'] == new_count:
        print(f"SUCCESS: Flock updated to {new_count}")
    else:
        print(f"FAILURE: Flock count is {target_flock['initial_count']}, expected {new_count}")

    # 5. Determine Deletion Persistence
    # Assuming the first mortality event ID is retrievable
    if not events:
        print("Skipping delete test (no events).")
        return

    evt_id = events[0]['id']
    print(f"Deleting mortality event {evt_id}...")
    res = requests.delete(f"{BASE_URL}/events/mortality/{evt_id}", headers=headers)
    
    if res.status_code != 204:
        print(f"Failed to delete event: {res.text}")
        return
    
    # Verify deletion
    res = requests.get(f"{BASE_URL}/events/mortality?flock_id={flock_id}", headers=headers)
    remaining_events = res.json()
    if not any(e['id'] == evt_id for e in remaining_events):
        print("SUCCESS: Event deleted and verified.")
    else:
        print("FAILURE: Event still exists after deletion.")

if __name__ == "__main__":
    run_test()
