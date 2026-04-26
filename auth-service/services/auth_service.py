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
        user_org_id: str,
    ) -> bool:
        """Check if user has super_user role"""
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            user_org_uuid = UUID(user_org_id) if isinstance(user_org_id, str) else user_org_id

            result = await db.execute(
                select(User).options(selectinload(User.roles)).where(User.id == user_uuid)
            )
            user = result.scalar_one_or_none()

            if not user:
                return False

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
        """Check if user is admin for a specific organization"""
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

            result = await db.execute(
                select(User).options(selectinload(User.roles)).where(User.id == user_uuid)
            )
            user = result.scalar_one_or_none()

            if not user:
                return False

            admin_result = await db.execute(
                select(Role).where(
                    Role.organization_id == org_id,
                    Role.name == "admin"
                )
            )
            admin_role = admin_result.scalar_one_or_none()

            return bool(admin_role and admin_role in user.roles)

        except Exception:
            return False

    @staticmethod
    async def verify_org_ownership_or_admin(
        db: AsyncSession,
        user_id: str,
        user_org_id: str,
        requested_org_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify user can access an organization.
        
        Access Rules:
        - Super Users (super_user role) can access any organization
        - Organization Admins can access only their own organization
        - Regular users can only access their own organization
        
        Returns:
            (is_authorized: bool, error_message: Optional[str])
        """
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            user_org_uuid = UUID(user_org_id) if isinstance(user_org_id, str) else user_org_id

            # Check for super_user role (can access any organization)
            is_super = await AuthService.is_super_user(db, user_id, user_org_id)
            if is_super:
                return True, None

            # For regular users and org admins, check if they belong to the organization
            if user_org_uuid != requested_org_id:
                return False, "Access denied: You can only access your own organization"

            # User belongs to the requested organization
            return True, None

        except Exception as e:
            return False, f"Authorization check failed: {str(e)}"
