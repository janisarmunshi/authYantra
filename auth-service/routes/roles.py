"""Endpoint and role management routes"""

from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload
from uuid import UUID
from database import get_db_session
from config import get_settings
from schemas import (
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    EndpointRegisterRequest,
    EndpointResponse,
    UserRoleAssignRequest,
)
from models import Organization, Role, User, RegisteredEndpoint
from services.auth_service import AuthService

settings = get_settings()
router = APIRouter(tags=["roles", "endpoints"])


# ==================== ENDPOINT REGISTRATION ====================

@router.post("/endpoints/{org_id}/register", response_model=dict)
async def register_endpoint(
    org_id: UUID,
    endpoint_data: EndpointRegisterRequest,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register available endpoints for an organization.
    
    This allows projects to register their API endpoints with available actions.
    Use this to track and manage which endpoints are available in your organization.
    
    Access Control:
    - Only Super Users and Organization Admins can register endpoints
    
    Request body:
    - endpoint: API endpoint path (e.g., "/api/users", "/api/reports", "/api/projects")
    - actions: List of available actions (e.g., ["read", "write", "delete", "modify"])
    - description: [Optional] Human-readable description of the endpoint
    
    Example:
    {
      "endpoint": "/api/users",
      "actions": ["read", "write", "delete"],
      "description": "User management endpoint"
    }
    
    Returns:
    - message: Success confirmation
    - endpoint: Endpoint registered
    - actions: Actions available
    """
    # Verify user
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    # Check if user can manage this organization
    is_super = await AuthService.is_super_user(db, user_id, user_org_id)
    is_admin = await AuthService.is_org_admin(db, user_id, org_id)
    
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins and super users can register endpoints")

    # Verify organization exists
    org_result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    if not org_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        # Check if endpoint already registered
        existing = await db.execute(
            select(RegisteredEndpoint).where(
                and_(
                    RegisteredEndpoint.organization_id == org_id,
                    RegisteredEndpoint.endpoint == endpoint_data.endpoint
                )
            )
        )
        existing_endpoint = existing.scalar_one_or_none()

        if existing_endpoint:
            # Update existing endpoint
            existing_endpoint.actions = endpoint_data.actions
            existing_endpoint.description = endpoint_data.description
            await db.commit()
            return {
                "message": "Endpoint updated successfully",
                "endpoint": endpoint_data.endpoint,
                "actions": endpoint_data.actions,
            }

        # Create new endpoint registration
        new_endpoint = RegisteredEndpoint(
            organization_id=org_id,
            endpoint=endpoint_data.endpoint,
            actions=endpoint_data.actions,
            description=endpoint_data.description,
        )
        db.add(new_endpoint)
        await db.commit()

        return {
            "message": "Endpoint registered successfully",
            "endpoint": endpoint_data.endpoint,
            "actions": endpoint_data.actions,
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error registering endpoint: {str(e)}")


@router.get("/endpoints/{org_id}")
async def list_registered_endpoints(
    org_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all registered endpoints for an organization.
    
    Access Control:
    - Users can only view endpoints for their own organization
    - Super Users can view endpoints for any organization
    
    Returns:
    - List of registered endpoints with actions and descriptions
    """
    # Verify user
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    # Check access
    is_authorized, error = await AuthService.verify_org_ownership_or_admin(
        db, user_id, user_org_id, org_id
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    try:
        result = await db.execute(
            select(RegisteredEndpoint).where(
                RegisteredEndpoint.organization_id == org_id
            )
        )
        endpoints = result.scalars().all()

        return [
            {
                "id": str(endpoint.id),
                "endpoint": endpoint.endpoint,
                "actions": endpoint.actions,
                "description": endpoint.description,
                "created_at": endpoint.created_at,
                "updated_at": endpoint.updated_at,
            }
            for endpoint in endpoints
        ]

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching endpoints: {str(e)}")


# ==================== ROLE MANAGEMENT ====================

@router.post("/roles/{org_id}", response_model=RoleResponse)
async def create_role(
    org_id: UUID,
    role_data: RoleCreate,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new role with specific endpoint permissions.
    
    Access Control:
    - Only Super Users and Organization Admins can create roles
    
    Request body:
    - name: Role name (e.g., "viewer", "editor", "moderator")
    - permissions: Dictionary mapping endpoints to allowed actions
    
    Example:
    {
      "name": "viewer",
      "permissions": {
        "/api/users": ["read"],
        "/api/reports": ["read"]
      }
    }
    
    Another example:
    {
      "name": "editor",
      "permissions": {
        "/api/users": ["read", "write"],
        "/api/reports": ["read", "write"],
        "/api/projects": ["read", "write", "delete"]
      }
    }
    
    Available actions: read, write, delete, modify
    
    Returns:
    - Role with id, name, permissions, and timestamps
    """
    # Verify user
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    # Check if user can manage this organization
    is_super = await AuthService.is_super_user(db, user_id, user_org_id)
    is_admin = await AuthService.is_org_admin(db, user_id, org_id)
    
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins and super users can create roles")

    try:
        # Verify organization exists
        org_result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        if not org_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Organization not found")

        # Check if role name already exists in organization
        existing_role = await db.execute(
            select(Role).where(
                and_(
                    Role.organization_id == org_id,
                    Role.name == role_data.name
                )
            )
        )
        if existing_role.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Role name already exists in this organization")

        # Create role
        new_role = Role(
            organization_id=org_id,
            name=role_data.name,
            permissions=role_data.permissions,
            is_active=True,
        )
        db.add(new_role)
        await db.commit()
        await db.refresh(new_role)
        return new_role

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating role: {str(e)}")


@router.patch("/roles/{org_id}/{role_id}", response_model=RoleResponse)
async def update_role(
    org_id: UUID,
    role_id: UUID,
    role_data: RoleUpdate,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update an existing role.
    
    Access Control:
    - Only Super Users and Organization Admins can update roles
    
    Can update:
    - name: New role name
    - permissions: New permission list
    - is_active: Activate/deactivate role
    """
    # Verify user
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    # Check if user can manage this organization
    is_super = await AuthService.is_super_user(db, user_id, user_org_id)
    is_admin = await AuthService.is_org_admin(db, user_id, org_id)
    
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins and super users can update roles")

    try:
        # Get role
        result = await db.execute(
            select(Role).where(
                and_(
                    Role.id == role_id,
                    Role.organization_id == org_id
                )
            )
        )
        role = result.scalar_one_or_none()

        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Prevent modifying system roles (admin, user, super_user)
        if role.name in ["admin", "user", "super_user"]:
            raise HTTPException(status_code=400, detail="Cannot modify system roles")

        # Update fields
        if role_data.name:
            role.name = role_data.name
        if role_data.permissions is not None:
            role.permissions = role_data.permissions
        if role_data.is_active is not None:
            role.is_active = role_data.is_active

        await db.commit()
        await db.refresh(role)
        return role

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error updating role: {str(e)}")


@router.delete("/roles/{org_id}/{role_id}")
async def delete_role(
    org_id: UUID,
    role_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete a role.
    
    Access Control:
    - Only Super Users and Organization Admins can delete roles
    
    Returns:
    - message: Success confirmation
    """
    # Verify user
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    # Check if user can manage this organization
    is_super = await AuthService.is_super_user(db, user_id, user_org_id)
    is_admin = await AuthService.is_org_admin(db, user_id, org_id)
    
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins and super users can delete roles")

    try:
        # Get role
        result = await db.execute(
            select(Role).where(
                and_(
                    Role.id == role_id,
                    Role.organization_id == org_id
                )
            )
        )
        role = result.scalar_one_or_none()

        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Prevent deleting system roles
        if role.name in ["admin", "user", "super_user"]:
            raise HTTPException(status_code=400, detail="Cannot delete system roles")

        await db.delete(role)
        await db.commit()
        return {"message": "Role deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting role: {str(e)}")


@router.get("/roles/{org_id}")
async def list_roles(
    org_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all roles for an organization.
    
    Access Control:
    - Users can only view roles for their own organization
    - Super Users can view any organization's roles
    """
    # Verify user
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    # Check access
    is_authorized, error = await AuthService.verify_org_ownership_or_admin(
        db, user_id, user_org_id, org_id
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    result = await db.execute(
        select(Role).where(Role.organization_id == org_id)
    )
    roles = result.scalars().all()

    return [
        {
            "id": role.id,
            "name": role.name,
            "permissions": role.permissions,
            "is_active": role.is_active,
            "created_at": role.created_at,
        }
        for role in roles
    ]


# ==================== USER ROLE ASSIGNMENT ====================

@router.post("/users/{user_id}/roles/{org_id}")
async def assign_role_to_user(
    user_id: UUID,
    org_id: UUID,
    role_assignment: UserRoleAssignRequest,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Assign a role to a user.
    
    Access Control:
    - Only Organization Admins and Super Users can assign roles
    
    Request body:
    - role_id: ID of the role to assign
    
    Returns:
    - message: Success confirmation
    - user_id: User ID
    - role_id: Assigned role ID
    """
    # Verify admin/superuser
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    admin_user_id = user_info.get("user_id")
    admin_org_id = user_info.get("org_id")

    # Check if admin can manage this organization
    is_super = await AuthService.is_super_user(db, admin_user_id, admin_org_id)
    is_admin = await AuthService.is_org_admin(db, admin_user_id, org_id)
    
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins and super users can assign roles")

    try:
        # Get user with roles eagerly loaded
        user_result = await db.execute(
            select(User).options(selectinload(User.roles)).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify user belongs to organization
        if user.organization_id != org_id:
            raise HTTPException(status_code=400, detail="User does not belong to this organization")

        # Get role
        role_result = await db.execute(
            select(Role).where(
                and_(
                    Role.id == role_assignment.role_id,
                    Role.organization_id == org_id
                )
            )
        )
        role = role_result.scalar_one_or_none()

        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Check if user already has this role
        if role in user.roles:
            raise HTTPException(status_code=400, detail="User already has this role")

        # Assign role
        user.roles.append(role)
        await db.commit()

        return {
            "message": "Role assigned successfully",
            "user_id": str(user_id),
            "role_id": str(role_assignment.role_id),
            "role_name": role.name,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error assigning role: {str(e)}")


@router.delete("/users/{user_id}/roles/{org_id}/{role_id}")
async def remove_role_from_user(
    user_id: UUID,
    org_id: UUID,
    role_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Remove a role from a user.
    
    Access Control:
    - Only Organization Admins and Super Users can remove roles
    
    Returns:
    - message: Success confirmation
    """
    # Verify admin/superuser
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    admin_user_id = user_info.get("user_id")
    admin_org_id = user_info.get("org_id")

    # Check if admin can manage this organization
    is_super = await AuthService.is_super_user(db, admin_user_id, admin_org_id)
    is_admin = await AuthService.is_org_admin(db, admin_user_id, org_id)
    
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins and super users can remove roles")

    try:
        # Get user with roles eagerly loaded
        user_result = await db.execute(
            select(User).options(selectinload(User.roles)).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify user belongs to organization
        if user.organization_id != org_id:
            raise HTTPException(status_code=400, detail="User does not belong to this organization")

        # Get role
        role_result = await db.execute(
            select(Role).where(
                and_(
                    Role.id == role_id,
                    Role.organization_id == org_id
                )
            )
        )
        role = role_result.scalar_one_or_none()

        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Remove role
        if role in user.roles:
            user.roles.remove(role)
            await db.commit()

        return {"message": "Role removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error removing role: {str(e)}")


@router.get("/users/{org_id}")
async def list_users(
    org_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all users in an organization.

    Access Control:
    - Any authenticated member of the org can see the user list
    - Super Users can view users in any organization
    """
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    is_authorized, error = await AuthService.verify_org_ownership_or_admin(
        db, user_id, user_org_id, org_id
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    result = await db.execute(
        select(User).where(User.organization_id == org_id).order_by(User.created_at)
    )
    users = result.scalars().all()

    return [
        {
            "id": str(u.id),
            "organization_id": str(u.organization_id),
            "email": u.email,
            "username": u.username,
            "is_active": u.is_active,
            "entra_id": u.entra_id,
            "created_at": u.created_at,
            "updated_at": u.updated_at,
        }
        for u in users
    ]


@router.delete("/users/{org_id}/{user_id}")
async def delete_user(
    org_id: UUID,
    user_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete a user from an organization.

    Access Control:
    - Only admins and super users can delete users
    - Cannot delete yourself
    """
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    requester_id = user_info.get("user_id")
    requester_org_id = user_info.get("org_id")

    is_super = await AuthService.is_super_user(db, requester_id, requester_org_id)
    is_admin = await AuthService.is_org_admin(db, requester_id, org_id)
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins and super users can delete users")

    if str(user_id) == requester_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    result = await db.execute(
        select(User).where(User.id == user_id, User.organization_id == org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        await db.delete(user)
        await db.commit()
        return {"message": "User deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting user: {str(e)}")


@router.get("/users/{user_id}/roles/{org_id}")
async def list_user_roles(
    user_id: UUID,
    org_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all roles assigned to a user.
    
    Access Control:
    - Users can view their own roles
    - Admins can view roles for any user in their organization
    
    Returns:
    - List of roles with id, name, permissions, and is_active status
    """
    # Verify user
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    requester_id = user_info.get("user_id")
    requester_org_id = user_info.get("org_id")

    # Users can only view their own roles, unless they're admin
    if requester_id != str(user_id):
        is_super = await AuthService.is_super_user(db, requester_id, requester_org_id)
        is_admin = await AuthService.is_org_admin(db, requester_id, org_id)
        
        if not is_super and not is_admin:
            raise HTTPException(status_code=403, detail="You can only view your own roles")

    try:
        # Get user with roles eagerly loaded
        result = await db.execute(
            select(User).options(selectinload(User.roles)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.organization_id != org_id:
            raise HTTPException(status_code=400, detail="User does not belong to this organization")

        return [
            {
                "id": role.id,
                "name": role.name,
                "permissions": role.permissions,
                "is_active": role.is_active,
            }
            for role in user.roles
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching user roles: {str(e)}")
