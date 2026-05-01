from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from uuid import UUID
from models import User, Organization, UserOrganization
from typing import Optional, Tuple, List

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    async def register_user(
        db: AsyncSession,
        email: str,
        password: str,
        username: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[str]]:
        """Register a new user with no org affiliation."""
        try:
            existing = await db.execute(select(User).where(User.email == email))
            if existing.scalar_one_or_none():
                return None, "Email already registered"

            if username:
                taken = await db.execute(select(User).where(User.username == username))
                if taken.scalar_one_or_none():
                    return None, "Username already taken"

            new_user = User(
                email=email,
                username=username,
                password_hash=UserService.hash_password(password),
                is_active=True,
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            return new_user, None

        except IntegrityError:
            await db.rollback()
            return None, "Email already registered"
        except Exception as e:
            await db.rollback()
            return None, f"Error registering user: {str(e)}"

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Tuple[Optional[User], Optional[str]]:
        """Authenticate by email+password only (org-agnostic)."""
        try:
            result = await db.execute(
                select(User).where(User.email == email, User.is_active == True)
            )
            user = result.scalar_one_or_none()
            if not user:
                return None, "Invalid email or password"
            if not user.password_hash:
                return None, "This account uses SSO authentication only"
            if not UserService.verify_password(password, user.password_hash):
                return None, "Invalid email or password"
            return user, None
        except Exception as e:
            return None, f"Error authenticating user: {str(e)}"

    @staticmethod
    async def get_user_memberships(db: AsyncSession, user_id: UUID) -> List[UserOrganization]:
        """Return all org memberships for a user, with org loaded."""
        result = await db.execute(
            select(UserOrganization)
            .options(selectinload(UserOrganization.organization))
            .where(UserOrganization.user_id == user_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_user_to_org(
        db: AsyncSession,
        user_id: UUID,
        org_id: UUID,
        role: str = "member",
        set_default: bool = False,
    ) -> Tuple[Optional[UserOrganization], Optional[str]]:
        """Add user to org. If set_default, also update user.organization_id."""
        try:
            existing = await db.execute(
                select(UserOrganization).where(
                    UserOrganization.user_id == user_id,
                    UserOrganization.org_id == org_id,
                )
            )
            if existing.scalar_one_or_none():
                return None, "User is already a member of this organization"

            if set_default:
                # Clear existing default
                await db.execute(
                    select(UserOrganization).where(
                        UserOrganization.user_id == user_id,
                        UserOrganization.is_default == True,
                    )
                )
                existing_defaults = await db.execute(
                    select(UserOrganization).where(
                        UserOrganization.user_id == user_id,
                        UserOrganization.is_default == True,
                    )
                )
                for m in existing_defaults.scalars().all():
                    m.is_default = False

            membership = UserOrganization(
                user_id=user_id,
                org_id=org_id,
                role=role,
                is_default=set_default,
            )
            db.add(membership)

            if set_default:
                user_result = await db.execute(select(User).where(User.id == user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    user.organization_id = org_id

            await db.commit()
            await db.refresh(membership)
            return membership, None
        except Exception as e:
            await db.rollback()
            return None, f"Error adding user to org: {str(e)}"

    @staticmethod
    async def set_default_org(db: AsyncSession, user_id: UUID, org_id: UUID) -> Tuple[bool, Optional[str]]:
        """Set a user's default org (must already be a member)."""
        try:
            membership_result = await db.execute(
                select(UserOrganization).where(
                    UserOrganization.user_id == user_id,
                    UserOrganization.org_id == org_id,
                )
            )
            membership = membership_result.scalar_one_or_none()
            if not membership:
                return False, "User is not a member of this organization"

            # Clear old default
            old_defaults = await db.execute(
                select(UserOrganization).where(
                    UserOrganization.user_id == user_id,
                    UserOrganization.is_default == True,
                )
            )
            for m in old_defaults.scalars().all():
                m.is_default = False

            membership.is_default = True

            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if user:
                user.organization_id = org_id

            await db.commit()
            return True, None
        except Exception as e:
            await db.rollback()
            return False, f"Error setting default org: {str(e)}"

    @staticmethod
    async def remove_user_from_org(
        db: AsyncSession, user_id: UUID, org_id: UUID
    ) -> Tuple[bool, Optional[str]]:
        """Remove a user from an org. Clears default if needed."""
        try:
            membership_result = await db.execute(
                select(UserOrganization).where(
                    UserOrganization.user_id == user_id,
                    UserOrganization.org_id == org_id,
                )
            )
            membership = membership_result.scalar_one_or_none()
            if not membership:
                return False, "User is not a member of this organization"

            was_default = membership.is_default
            await db.delete(membership)

            if was_default:
                # Pick next membership as default, or null out user.organization_id
                next_result = await db.execute(
                    select(UserOrganization).where(UserOrganization.user_id == user_id)
                )
                next_membership = next_result.scalars().first()
                user_result = await db.execute(select(User).where(User.id == user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    if next_membership:
                        next_membership.is_default = True
                        user.organization_id = next_membership.org_id
                    else:
                        user.organization_id = None

            await db.commit()
            return True, None
        except Exception as e:
            await db.rollback()
            return False, f"Error removing user from org: {str(e)}"

    @staticmethod
    async def get_user_by_id(
        db: AsyncSession,
        user_id: UUID,
        organization_id: Optional[UUID] = None,
    ) -> Optional[User]:
        """Get user by ID. If organization_id provided, validates membership."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        if organization_id and user.organization_id != organization_id:
            # Check membership table as fallback
            m = await db.execute(
                select(UserOrganization).where(
                    UserOrganization.user_id == user_id,
                    UserOrganization.org_id == organization_id,
                )
            )
            if not m.scalar_one_or_none():
                return None
        return user

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: UUID) -> list:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return []
        await db.refresh(user, ["roles"])
        return [role.name for role in user.roles]

    @staticmethod
    async def update_password(
        db: AsyncSession, user_id: UUID, new_password: str
    ) -> Tuple[bool, Optional[str]]:
        try:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return False, "User not found"
            user.password_hash = UserService.hash_password(new_password)
            await db.commit()
            return True, None
        except Exception as e:
            await db.rollback()
            return False, f"Error updating password: {str(e)}"
