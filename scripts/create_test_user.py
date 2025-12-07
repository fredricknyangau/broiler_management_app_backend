from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.security import get_password_hash

def create_test_user():
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing = db.query(User).filter(User.email == "farmer@example.com").first()
        if existing:
            print(f"⚠️  User already exists: {existing.email}")
            print(f"   ID: {existing.id}")
            return
        
        # Create new user
        user = User(
            email="farmer@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="John Kamau",
            phone_number="+254712345678",
            location="Kiambu, Kenya"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"✅ User created successfully!")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Name: {user.full_name}")
        print(f"   Location: {user.location}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
