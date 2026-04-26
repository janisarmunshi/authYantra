"""Organization and registered-app management routes"""

import secrets
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from pydantic import BaseModel
from database import get_db_session
from models import Organization, RegisteredApp, User
from schemas import OrganizationCreate, RegisteredAppCreate
from services.auth_service import AuthService

router = APIRouter(tags=["organizations", "apps"])


# ── Request body for Entra ID update (field names match the frontend) ─────────

class EntraIdUpdate(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str


# ── Helper: serialize Organization ────────────────────────────────────────────

def _org_dict(org: Organization) -> dict:
    return {
        "id": str(org.id),
        "name": org.name,
        "entra_id_tenant_id": org.entra_id_tenant_id,
        "entra_id_client_id": org.entra_id_client_id,
        "is_active": org.is_active,
        "created_at": org.created_at,
        "updated_at": org.updated_at,
    }


def _app_dict(app: RegisteredApp) -> dict:
    return {
        "id": str(app.id),
        "organization_id": str(app.organization_id),
        "app_name": app.app_name,
        "app_type": app.app_type,
        "api_key": app.api_key,
        "redirect_uris": app.redirect_uris,
        "is_active": app.is_active,
        "created_at": app.created_at,
        "updated_at": app.updated_at,
    }


# ── Organizations ─────────────────────────────────────────────────────────────

@router.post("/orgs")
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new organization (no auth required — used for initial setup)."""
    org = Organization(name=data.name)
    db.add(org)
    try:
        await db.commit()
        await db.refresh(org)
        return _org_dict(org)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating organization: {str(e)}")


@router.get("/orgs/{org_id}")
async def get_organization(
    org_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Get organization by ID. Users can only access their own org."""
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

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _org_dict(org)


@router.patch("/orgs/{org_id}/entra")
async def update_entra_id(
    org_id: UUID,
    data: EntraIdUpdate,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Update Entra ID (Azure AD) SSO configuration. Admin only."""
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    is_super = await AuthService.is_super_user(db, user_id, user_org_id)
    is_admin = await AuthService.is_org_admin(db, user_id, org_id)
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.entra_id_tenant_id = data.tenant_id  # type: ignore[assignment]
    org.entra_id_client_id = data.client_id  # type: ignore[assignment]
    org.entra_id_client_secret = data.client_secret.encode()  # type: ignore[assignment]
    try:
        await db.commit()
        await db.refresh(org)
        return _org_dict(org)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error updating Entra ID config: {str(e)}")


# ── Registered Apps ───────────────────────────────────────────────────────────

@router.post("/orgs/{org_id}/apps")
async def create_app(
    org_id: UUID,
    data: RegisteredAppCreate,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new application. Admin only."""
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info.get("user_id")
    user_org_id = user_info.get("org_id")

    is_super = await AuthService.is_super_user(db, user_id, user_org_id)
    is_admin = await AuthService.is_org_admin(db, user_id, org_id)
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    if not org_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Organization not found")

    app = RegisteredApp(
        organization_id=org_id,
        app_name=data.app_name,
        app_type=data.app_type,
        api_key=secrets.token_urlsafe(32),
        redirect_uris=data.redirect_uris,
    )
    db.add(app)
    try:
        await db.commit()
        await db.refresh(app)
        return _app_dict(app)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating app: {str(e)}")


@router.get("/orgs/{org_id}/apps/{app_id}")
async def get_app(
    org_id: UUID,
    app_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Get a registered application by ID. Any org member can view."""
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
        select(RegisteredApp).where(
            RegisteredApp.id == app_id,
            RegisteredApp.organization_id == org_id,
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return _app_dict(app)
