"""Authorization and access control service"""

from typing import Optional, Tuple
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import User, Organization, Role
from services.token_service import TokenService
from sqlalchemy.orm import selectinload


class AuthService:
    """Service for authorization and access control"""

    @staticmethod
    def verify_and_get_user(authorization_header: str) -> Optional[dict]:
        """
        Verify JWT token and extract user info.
        Returns: dict with {sub (user_id), org_id, email} or None if invalid
        """
        token = TokenService.get_token_from_header(authorization_header)
        if not token:
            return None

        payload = TokenService.verify_access_token(token)
        if not payload:
            return None

        return {
            "user_id": payload.get("sub"),
            "org_id": payload.get("org_id"),
            "email": payload.get("email"),
        }

    @staticmethod
    async def verify_org_access(
        db: AsyncSession,
        user_id: str,
        organization_id: UUID,
        require_admin: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify that a user has access to an organization.
        
        Args:
            db: Database session
            user_id: User ID from JWT token
            organization_id: Organization ID to access
            require_admin: If True, user must be admin to access
            
        Returns:
            (is_authorized: bool, error_message: Optional[str])
        """
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

            # Get user with roles
            result = await db.execute(
                select(User).where(User.id == user_uuid)
            )
            user = result.scalar_one_or_none()

            if not user:
                return False, "User not found"

            # Check if user belongs to the organization
            if user.organization_id != organization_id:
                return False, "Access denied: User does not belong to this organization"

            # If admin access required, check for admin role
            if require_admin:
                # Get admin role for this organization
                from models import Role
                admin_role_result = await db.execute(
                    select(Role).where(
                        Role.organization_id == organization_id,
                        Role.name == "admin"
                    )
                )
                admin_role = admin_role_result.scalar_one_or_none()

                if not admin_role or admin_role not in user.roles:
                    return False, "Access denied: Admin privileges required"

            return True, None

        except Exception as e:
            return False, f"Authorization check failed: {str(e)}"

    @staticmethod
    async def is_super_user(
        db: AsyncSession,
        user_id: str,
        user_org_id: Optional[str],
    ) -> bool:
        """Check if user has super_user role"""
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

            result = await db.execute(
                select(User).options(selectinload(User.roles)).where(User.id == user_uuid)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            if not user_org_id:
                return False

            user_org_uuid = UUID(user_org_id) if isinstance(user_org_id, str) else user_org_id
            super_user_result = await db.execute(
                select(Role).where(
                    Role.organization_id == user_org_uuid,
                    Role.name == "super_user"
                )
            )
            super_user_role = super_user_result.scalar_one_or_none()
            return bool(super_user_role and super_user_role in user.roles)

        except Exception:
            return False

    @staticmethod
    async def is_org_admin(
        db: AsyncSession,
        user_id: str,
        org_id: UUID,
    ) -> bool:
        """Check if user is admin for a specific organization.
        Uses user_organizations.role — the membership-level admin flag."""
        try:
            from models import UserOrganization
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

            result = await db.execute(
                select(UserOrganization).where(
                    UserOrganization.user_id == user_uuid,
                    UserOrganization.org_id == org_id,
                    UserOrganization.role == "admin",
                )
            )
            return result.scalar_one_or_none() is not None

        except Exception:
            return False

    @staticmethod
    async def verify_org_ownership_or_admin(
        db: AsyncSession,
        user_id: str,
        user_org_id: Optional[str],
        requested_org_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify user can access an organization.

        Access Rules:
        - Super Users can access any organization
        - Regular users/admins must be a member of the org (checked via user_organizations table)
        """
        try:
            from models import UserOrganization
            from sqlalchemy import select as sa_select

            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

            is_super = await AuthService.is_super_user(db, user_id, user_org_id)
            if is_super:
                return True, None

            # Check membership table
            m = await db.execute(
                sa_select(UserOrganization).where(
                    UserOrganization.user_id == user_uuid,
                    UserOrganization.org_id == requested_org_id,
                )
            )
            if m.scalar_one_or_none():
                return True, None

            # Fallback: token org_id matches
            if user_org_id:
                try:
                    if UUID(user_org_id) == requested_org_id:
                        return True, None
                except Exception:
                    pass

            return False, "Access denied: You are not a member of this organization"

        except Exception as e:
            return False, f"Authorization check failed: {str(e)}"
