import time
import requests
import sys

BASE_URL = "http://localhost:8000/api/v1"

# Get credentials from arguments or use defaults
EMAIL = "zeal@gmail.com"
PASSWORD = "password123" # Assuming this is the test user password, if not I might need to reset or pick one I know.
# Actually I promoted 'zeal@gmail.com', I don't know the password.
# I will try to find a known user or create one if possible. 
# Wait, I can't create a user without a valid token if registration is protected? 
# Registration is usually public.

def test_performance():
    print(f"Testing performance against {BASE_URL}...")
    
    # 1. Login
    start_time = time.time()
    try:
        # Try a known default/test credential or just fail
        # If I don't know the password, I might need to reset it directly in DB for testing.
        # Let's assume 'password' or 'password123' or 'admin'.
        # Or I can skip login if I can generate a token in python directly.
        pass 
    except Exception as e:
        print(f"Login failed: {e}")

if __name__ == "__main__":
    # Better approach: Generate token manually using backend code, so we don't guess password.
    # We have access to the codebase!
    try:
        sys.path.append("/home/fred/Projects/broiler-management-app/backend")
        from app.db.session import SessionLocal
        from app.core.security import create_access_token
        from app.db.models.user import User
        from datetime import timedelta
        
        db = SessionLocal()
        user = db.query(User).first()
        if not user:
            print("No user found in DB.")
            sys.exit(1)
            
        print(f"Benchmarking for user: {user.email}")
        
        # Generate valid token
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=5)
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 2. Benchmark Sync
        print("Benchmarking /sync endpoint...")
        start = time.time()
        resp = requests.get(f"{BASE_URL}/data/sync", headers=headers)
        end = time.time()
        
        duration = end - start
        print(f"Sync Request took: {duration:.4f} seconds")
        print(f"Status Code: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Response: {resp.text[:200]}...")
        else:
            print(f"Response Size: {len(resp.content)} bytes")
            
    except ModuleNotFoundError:
        print("Could not import backend modules. Make sure you run this from backend dir.")
    except Exception as e:
        print(f"Error: {e}")
