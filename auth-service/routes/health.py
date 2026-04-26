from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
import secrets
from database import get_db_session
from config import get_settings
from schemas import (
    HealthResponse,
    OrganizationCreate,
    OrganizationEntraIDUpdate,
    OrganizationResponse,
    RegisteredAppCreate,
    RegisteredAppResponse,
)
from models import Organization, RegisteredApp, Role
from services.auth_service import AuthService

settings = get_settings()
router = APIRouter(tags=["health", "management"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENV,
    )


@router.post("/orgs", response_model=OrganizationResponse)
async def create_organization(
    org_data: OrganizationCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new organization with default roles.
    
    Automatically creates:
    - admin role: Full control over all endpoints
    - user role: Read-only access to basic endpoints
    """
    try:
        new_org = Organization(
            name=org_data.name,
            entra_id_tenant_id=org_data.entra_id_tenant_id,
        )
        db.add(new_org)
        await db.flush()  # Flush to get the org ID before creating roles

        # Create default roles for the organization
        admin_role = Role(
            organization_id=new_org.id,
            name="admin",
            permissions={
                "/api/*": ["read", "write", "delete", "modify"]  # Full access to all endpoints
            },
            is_active=True,
        )
        db.add(admin_role)

        user_role = Role(
            organization_id=new_org.id,
            name="user",
            permissions={
                "/api/users": ["read"],  # Read-only to users endpoint
                "/api/reports": ["read"]  # Read-only to reports endpoint
            },
            is_active=True,
        )
        db.add(user_role)

        await db.commit()
        await db.refresh(new_org)
        return new_org
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating organization: {str(e)}")


@router.get("/orgs/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get organization details.
    
    Access Control:
    - Users can only view their own organization
    - Admins can view any organization
    
    Required Headers:
    - Authorization: Bearer {access_token}
    """
    # Verify user and token
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    # Check if user can access this organization
    is_authorized, error = await AuthService.verify_org_ownership_or_admin(
        db, user_id, user_org_id, org_id
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return org


@router.patch("/orgs/{org_id}/entra", response_model=OrganizationResponse)
async def configure_entra_id(
    org_id: UUID,
    entra_config: OrganizationEntraIDUpdate,
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Configure Microsoft Entra ID credentials for an organization.
    
    **Multi-Organization Design**: Each organization stores its own Entra ID credentials
    in the database. The .env file is only used as fallback for backward compatibility.
    For production multi-tenant setups, always use this endpoint to configure per-org credentials.
    
    Access Control:
    - Only admins can configure Entra ID for organizations
    
    Required Headers:
    - Authorization: Bearer {access_token}
    
    Request body requires:
    - entra_id_tenant_id: Azure Directory/Tenant ID
    - entra_id_client_id: Azure Application (Client) ID  
    - entra_id_client_secret: Azure Client Secret value
    """
    # Verify user and token
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    # Check if user can access this organization
    is_authorized, error = await AuthService.verify_org_ownership_or_admin(
        db, user_id, user_org_id, org_id
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    try:
        result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Update Entra ID configuration
        org.entra_id_tenant_id = entra_config.entra_id_tenant_id
        org.entra_id_client_id = entra_config.entra_id_client_id
        
        # Store client secret as bytes (can be encrypted in production)
        org.entra_id_client_secret = entra_config.entra_id_client_secret.encode()

        await db.commit()
        await db.refresh(org)
        return org
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error configuring Entra ID: {str(e)}")


@router.post("/orgs/{org_id}/apps", response_model=RegisteredAppResponse)
async def register_app(
    org_id: UUID,
    app_data: RegisteredAppCreate,
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register an application for an organization.
    
    Access Control:
    - Users can only register apps for their own organization
    - Admins can register apps for any organization
    
    Required Headers:
    - Authorization: Bearer {access_token}
    """
    # Verify user and token
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    # Check if user can access this organization
    is_authorized, error = await AuthService.verify_org_ownership_or_admin(
        db, user_id, user_org_id, org_id
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    try:
        # Check if org exists
        result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Generate API key
        api_key = f"app_{secrets.token_urlsafe(32)}"

        new_app = RegisteredApp(
            organization_id=org_id,
            app_name=app_data.app_name,
            app_type=app_data.app_type,
            api_key=api_key,
            redirect_uris=app_data.redirect_uris,
        )
        db.add(new_app)
        await db.commit()
        await db.refresh(new_app)
        return new_app
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error registering app: {str(e)}")


@router.get("/orgs/{org_id}/apps/{app_id}", response_model=RegisteredAppResponse)
async def get_app(
    org_id: UUID,
    app_id: UUID,
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get registered app details.
    
    Access Control:
    - Users can only view apps for their own organization
    - Admins can view apps for any organization
    
    Required Headers:
    - Authorization: Bearer {access_token}
    """
    # Verify user and token
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    # Check if user can access this organization
    is_authorized, error = await AuthService.verify_org_ownership_or_admin(
        db, user_id, user_org_id, org_id
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    result = await db.execute(
        select(RegisteredApp).where(
            and_(
                RegisteredApp.id == app_id,
                RegisteredApp.organization_id == org_id,
            )
        )
    )
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    return app
