"""Organization, membership, and registered-app management routes"""

import hashlib
import secrets
import uuid as _uuid
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime, timedelta
from database import get_db_session
from models import Organization, RegisteredApp, User, UserOrganization, OrgInvite
from schemas import (
    OrganizationCreate, RegisteredAppCreate,
    OrgMemberAdd, OrgMemberResponse, OrgInviteCreate, OrgInviteResponse,
)
from services.auth_service import AuthService
from services.user_service import UserService
from services.email_service import send_invite_email

router = APIRouter(tags=["organizations", "apps"])

INVITE_EXPIRE_HOURS = 72


class EntraIdUpdate(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str


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
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new organization. Creator becomes admin and it is auto-set as default if first org."""
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        user_id = UUID(user_info["user_id"])

        # Check membership count BEFORE opening the write transaction
        existing_memberships = await UserService.get_user_memberships(db, user_id)
        is_first = len(existing_memberships) == 0

        # Pre-generate UUID so we don't need db.flush() to get the org id
        org_id = _uuid.uuid4()
        org = Organization(id=org_id, name=data.name)
        db.add(org)

        membership = UserOrganization(
            user_id=user_id,
            org_id=org_id,
            role="admin",
            is_default=is_first,
        )
        db.add(membership)

        if is_first:
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if user:
                user.organization_id = org_id

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
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    is_authorized, error = await AuthService.verify_org_ownership_or_admin(
        db, user_info["user_id"], user_info.get("org_id"), org_id
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
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    user_id = user_info["user_id"]
    is_super = await AuthService.is_super_user(db, user_id, user_info.get("org_id"))
    is_admin = await AuthService.is_org_admin(db, user_id, org_id)
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.entra_id_tenant_id = data.tenant_id
    org.entra_id_client_id = data.client_id
    org.entra_id_client_secret = data.client_secret.encode()
    try:
        await db.commit()
        await db.refresh(org)
        return _org_dict(org)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error updating Entra ID config: {str(e)}")


# ── Members ───────────────────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/members", response_model=list[OrgMemberResponse])
async def list_members(
    org_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """List all members of an organization. Any member can view."""
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_authorized, error = await AuthService.verify_org_ownership_or_admin(
        db, user_info["user_id"], user_info.get("org_id"), org_id
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    result = await db.execute(
        select(UserOrganization)
        .options(selectinload(UserOrganization.user))
        .where(UserOrganization.org_id == org_id)
    )
    return [
        OrgMemberResponse(
            user_id=str(m.user_id),
            email=m.user.email,
            username=m.user.username,
            role=m.role,
            is_default=m.is_default,
            joined_at=m.joined_at,
        )
        for m in result.scalars().all()
    ]


@router.post("/orgs/{org_id}/members")
async def add_member(
    org_id: UUID,
    data: OrgMemberAdd,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Admin directly adds an existing user to the org by email."""
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_super = await AuthService.is_super_user(db, user_info["user_id"], user_info.get("org_id"))
    is_admin = await AuthService.is_org_admin(db, user_info["user_id"], org_id)
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    user = await UserService.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="No user found with that email")

    is_first = len(await UserService.get_user_memberships(db, user.id)) == 0
    _, error = await UserService.add_user_to_org(db, user.id, org_id, role=data.role, set_default=is_first)
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {"message": f"{data.email} added to organization", "user_id": str(user.id)}


@router.delete("/orgs/{org_id}/members/{user_id}")
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Remove a member. Admins can remove anyone; members can remove themselves."""
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Authentication required")

    requester_id = user_info["user_id"]
    is_super = await AuthService.is_super_user(db, requester_id, user_info.get("org_id"))
    is_admin = await AuthService.is_org_admin(db, requester_id, org_id)
    if not is_super and not is_admin and str(user_id) != requester_id:
        raise HTTPException(status_code=403, detail="Admin access required")

    success, error = await UserService.remove_user_from_org(db, user_id, org_id)
    if not success:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Member removed from organization"}


# ── Invites ───────────────────────────────────────────────────────────────────

@router.post("/orgs/{org_id}/invite", response_model=OrgInviteResponse)
async def invite_member(
    org_id: UUID,
    data: OrgInviteCreate,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Send an invite email to join the organization. Admin only."""
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_super = await AuthService.is_super_user(db, user_info["user_id"], user_info.get("org_id"))
    is_admin = await AuthService.is_org_admin(db, user_info["user_id"], org_id)
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Reject if already a member
    existing_user = await UserService.get_user_by_email(db, data.email)
    if existing_user:
        m = await db.execute(
            select(UserOrganization).where(
                UserOrganization.user_id == existing_user.id,
                UserOrganization.org_id == org_id,
            )
        )
        if m.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User is already a member")

    # Invalidate previous pending invites for same email+org
    old = await db.execute(
        select(OrgInvite).where(
            OrgInvite.org_id == org_id,
            OrgInvite.invited_email == data.email,
            OrgInvite.accepted_at.is_(None),
        )
    )
    for old_invite in old.scalars().all():
        old_invite.accepted_at = datetime.utcnow()

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(hours=INVITE_EXPIRE_HOURS)

    invite = OrgInvite(
        org_id=org_id,
        invited_email=data.email,
        token_hash=token_hash,
        role=data.role,
        invited_by_user_id=UUID(user_info["user_id"]),
        expires_at=expires_at,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    from config import get_settings
    settings = get_settings()
    invite_link = f"{settings.FRONTEND_URL}/accept-invite?token={raw_token}"
    await send_invite_email(
        to_email=data.email,
        org_name=str(org.name),
        invite_link=invite_link,
        role=data.role,
        expires_hours=INVITE_EXPIRE_HOURS,
    )

    return OrgInviteResponse(
        id=str(invite.id),
        invited_email=invite.invited_email,
        role=invite.role,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
    )


@router.get("/orgs/{org_id}/invites", response_model=list[OrgInviteResponse])
async def list_invites(
    org_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """List pending invites for an org. Admin only."""
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_super = await AuthService.is_super_user(db, user_info["user_id"], user_info.get("org_id"))
    is_admin = await AuthService.is_org_admin(db, user_info["user_id"], org_id)
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(
        select(OrgInvite).where(
            OrgInvite.org_id == org_id,
            OrgInvite.accepted_at.is_(None),
            OrgInvite.expires_at > datetime.utcnow(),
        )
    )
    return [
        OrgInviteResponse(
            id=str(i.id), invited_email=i.invited_email,
            role=i.role, expires_at=i.expires_at, accepted_at=i.accepted_at,
        )
        for i in result.scalars().all()
    ]


# ── Registered Apps ───────────────────────────────────────────────────────────

@router.post("/orgs/{org_id}/apps")
async def create_app(
    org_id: UUID,
    data: RegisteredAppCreate,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    is_super = await AuthService.is_super_user(db, user_info["user_id"], user_info.get("org_id"))
    is_admin = await AuthService.is_org_admin(db, user_info["user_id"], org_id)
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


@router.get("/orgs/{org_id}/apps")
async def list_apps(
    org_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    is_authorized, error = await AuthService.verify_org_ownership_or_admin(
        db, user_info["user_id"], user_info.get("org_id"), org_id
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail=error or "Access denied")

    result = await db.execute(
        select(RegisteredApp).where(RegisteredApp.organization_id == org_id).order_by(RegisteredApp.created_at)
    )
    return [_app_dict(a) for a in result.scalars().all()]


@router.delete("/orgs/{org_id}/apps/{app_id}")
async def delete_app(
    org_id: UUID,
    app_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_super = await AuthService.is_super_user(db, user_info["user_id"], user_info.get("org_id"))
    is_admin = await AuthService.is_org_admin(db, user_info["user_id"], org_id)
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(
        select(RegisteredApp).where(RegisteredApp.id == app_id, RegisteredApp.organization_id == org_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    await db.delete(app)
    await db.commit()
    return {"message": "App deleted"}


@router.delete("/orgs/{org_id}")
async def delete_organization(
    org_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete an organization and all its related data. Admin only."""
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_super = await AuthService.is_super_user(db, user_info["user_id"], user_info.get("org_id"))
    is_admin = await AuthService.is_org_admin(db, user_info["user_id"], org_id)
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        await db.delete(org)
        await db.commit()
        return {"message": "Organization deleted"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting organization: {str(e)}")


@router.get("/orgs/{org_id}/apps/{app_id}")
async def get_app(
    org_id: UUID,
    app_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization")

    is_authorized, error = await AuthService.verify_org_ownership_or_admin(
        db, user_info["user_id"], user_info.get("org_id"), org_id
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
