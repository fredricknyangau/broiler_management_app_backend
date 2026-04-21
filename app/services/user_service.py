from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.db.models.user import User


class UserService:
    """Service for user operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def normalize_phone(phone_number: str | None) -> str | None:
        """Normalize Kenyan phone numbers so lookups and storage are consistent."""
        if not phone_number:
            return phone_number

        phone = phone_number.strip().replace(" ", "").replace("-", "")
        if phone.startswith("0"):
            phone = "+254" + phone[1:]
        elif phone.startswith("254") and not phone.startswith("+"):
            phone = "+" + phone
        return phone

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(select(User).filter(User.id == user_id))
        return result.scalars().first()

    async def create_user(self, email: str, password: str, **kwargs) -> User:
        """Create a new user"""
        if "phone_number" in kwargs:
            kwargs["phone_number"] = self.normalize_phone(kwargs["phone_number"])

        # Check if user already exists
        existing = await self.get_by_email(email)
        if existing:
            raise ValueError(f"User with email {email} already exists")

        # Create user
        hashed_password = get_password_hash(password)
        user = User(email=email, hashed_password=hashed_password, **kwargs)

        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        except Exception as e:
            await self.db.rollback()
            # If it's an integrity error, we might want to be specific,
            # but for now, generic catching or re-raising as ValueError helps the API layer
            if "unique constraint" in str(e).lower():
                raise ValueError("User with this email or phone number already exists")
            raise e

        return user

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await self.get_by_email(email)

        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    async def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """Update user details"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if "phone_number" in kwargs:
            kwargs["phone_number"] = self.normalize_phone(kwargs["phone_number"])

        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def get_by_phone(self, phone_number: str) -> Optional[User]:
        """Get user by phone number"""
        phone_number = self.normalize_phone(phone_number)
        result = await self.db.execute(
            select(User).filter(User.phone_number == phone_number)
        )
        return result.scalars().first()

    async def get_or_create_user_by_phone(self, phone_number: str) -> tuple[User, bool]:
        """Get or create user by phone number (Passwordless)"""
        phone_number = self.normalize_phone(phone_number)
        user = await self.get_by_phone(phone_number)
        if user:
            return user, False

        # Create full skeleton account
        user = User(phone_number=phone_number, is_active=True, role="FARMER")

        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        except Exception as e:
            await self.db.rollback()
            raise e

        return user, True

    async def get_or_create_user_by_email(
        self,
        email: str,
        full_name: str | None = None,
        sso_provider: str | None = None,
    ) -> tuple[User, bool]:
        """Get or create an SSO-backed user by email."""
        normalized_email = email.strip().lower()
        user = await self.get_by_email(normalized_email)
        if user:
            updated = False
            if full_name and not user.full_name:
                user.full_name = full_name
                updated = True
            if updated:
                await self.db.commit()
                await self.db.refresh(user)
            return user, False

        user = User(
            email=normalized_email,
            full_name=full_name,
            is_active=True,
            role="FARMER",
        )

        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        except Exception as e:
            await self.db.rollback()
            raise e

        return user, True
