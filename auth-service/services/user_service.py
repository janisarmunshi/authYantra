from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from models import User, Organization
from typing import Optional, Tuple

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Service for handling user operations"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    async def register_user(
        db: AsyncSession,
        organization_id: UUID,
        email: str,
        password: str,
        username: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new local user.
        Returns: (user, error_message)
        """
        try:
            # Check if organization exists
            org_result = await db.execute(
                select(Organization).where(Organization.id == organization_id)
            )
            org = org_result.scalar_one_or_none()
            if not org:
                return None, "Organization not found"

            # Check if email already exists in organization
            email_result = await db.execute(
                select(User).where(
                    User.email == email,
                    User.organization_id == organization_id,
                )
            )
            if email_result.scalar_one_or_none():
                return None, "Email already registered in this organization"

            # Check if username exists (if provided)
            if username:
                username_result = await db.execute(
                    select(User).where(
                        User.username == username,
                        User.organization_id == organization_id,
                    )
                )
                if username_result.scalar_one_or_none():
                    return None, "Username already taken in this organization"

            # Create new user
            hashed_password = UserService.hash_password(password)
            new_user = User(
                organization_id=organization_id,
                email=email,
                username=username,
                password_hash=hashed_password,
                is_active=True,
            )

            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            return new_user, None

        except IntegrityError:
            await db.rollback()
            return None, "Database integrity error"
        except Exception as e:
            await db.rollback()
            return None, f"Error registering user: {str(e)}"

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        organization_id: UUID,
        email: str,
        password: str,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate a user with email and password.
        Returns: (user, error_message)
        """
        try:
            # Find user in organization
            result = await db.execute(
                select(User).where(
                    User.email == email,
                    User.organization_id == organization_id,
                    User.is_active == True,
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                return None, "Invalid email or password"

            # Check if user has local auth (password_hash)
            if not user.password_hash:
                return None, "This account uses SSO authentication only"

            # Verify password
            if not UserService.verify_password(password, user.password_hash):
                return None, "Invalid email or password"

            return user, None

        except Exception as e:
            return None, f"Error authenticating user: {str(e)}"

    @staticmethod
    async def get_user_by_id(
        db: AsyncSession,
        user_id: UUID,
        organization_id: UUID,
    ) -> Optional[User]:
        """Get user by ID, validating they belong to organization"""
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(
        db: AsyncSession,
        email: str,
        organization_id: UUID,
    ) -> Optional[User]:
        """Get user by email, validating they belong to organization"""
        result = await db.execute(
            select(User).where(
                User.email == email,
                User.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: UUID) -> list:
        """Get all role names for a user"""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return []

        # Load relationships
        await db.refresh(user, ["roles"])
        return [role.name for role in user.roles]
    @staticmethod
    async def update_password(
        db: AsyncSession,
        user_id: UUID,
        new_password: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Update user password.
        Returns: (success, error_message)
        """
        try:
            # Get user
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                return False, "User not found"

            # Hash new password
            hashed_password = UserService.hash_password(new_password)
            user.password_hash = hashed_password

            await db.commit()
            return True, None

        except Exception as e:
            await db.rollback()
            return False, f"Error updating password: {str(e)}"