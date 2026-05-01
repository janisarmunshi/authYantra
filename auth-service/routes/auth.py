import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from database import get_db_session
from schemas import (
    UserRegister, UserLogin, LoginResponse, TokenResponse,
    TokenRefreshRequest, TokenVerifyRequest, TokenVerifyResponse,
    UserResponse, ChangePasswordRequest, ForgotPasswordRequest,
    ResetPasswordRequest, ResetPasswordVerifyResponse,
    OrgSummary, OrgInviteAccept,
)
from services.user_service import UserService
from services.token_service import TokenService
from services.rate_limiter import limiter
from services.email_service import send_password_reset_email
from models import RefreshToken, PasswordResetToken, UserOrganization, Organization, OrgInvite, User
from datetime import datetime, timedelta
from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])


def _org_summaries(memberships) -> list[OrgSummary]:
    return [
        OrgSummary(
            id=str(m.org_id),
            name=m.organization.name if m.organization else "",
            role=m.role,
            is_default=m.is_default,
        )
        for m in memberships
    ]


async def _issue_tokens(db: AsyncSession, user, org_id) -> tuple[str, str]:
    roles = await UserService.get_user_roles(db, user.id)
    access_token = TokenService.create_access_token(user.id, org_id, roles)
    refresh_token = TokenService.create_refresh_token(user.id, org_id)

    token_hash = TokenService.hash_token(refresh_token)
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    await db.commit()
    return access_token, refresh_token


@router.post("/register", response_model=dict)
@limiter.limit("10/minute")
async def register(
    request: Request,
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user (no org required at signup)."""
    user, error = await UserService.register_user(
        db=db,
        email=user_data.email,
        password=user_data.password,
        username=user_data.username,
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "User registered successfully", "user_id": str(user.id)}


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Login with email and password.

    Response includes:
    - Tokens with an org context when a default/single org can be resolved.
    - `needs_org_selection: true` + `organizations` list when the user belongs to
      multiple orgs and has no default set — frontend should show an org picker
      and call POST /auth/switch-org/{org_id}.
    """
    user, error = await UserService.authenticate_user(
        db=db, email=credentials.email, password=credentials.password
    )
    if error:
        raise HTTPException(status_code=401, detail=error)

    memberships = await UserService.get_user_memberships(db, user.id)

    # Resolve active org
    active_org_id = None
    needs_selection = False

    if len(memberships) == 0:
        active_org_id = None
    elif len(memberships) == 1:
        active_org_id = memberships[0].org_id
        if not memberships[0].is_default:
            # auto-promote as default
            memberships[0].is_default = True
            user.organization_id = active_org_id
            await db.commit()
    else:
        default = next((m for m in memberships if m.is_default), None)
        if default:
            active_org_id = default.org_id
        else:
            needs_selection = True

    access_token, refresh_token = await _issue_tokens(db, user, active_org_id)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        org_id=str(active_org_id) if active_org_id else None,
        needs_org_selection=needs_selection,
        organizations=_org_summaries(memberships) if needs_selection else [],
    )


@router.get("/my-orgs", response_model=list[OrgSummary])
async def my_orgs(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """List all organizations the current user belongs to."""
    user_info = TokenService.verify_access_token(
        TokenService.get_token_from_header(authorization)
    )
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    memberships = await UserService.get_user_memberships(db, UUID(user_info["sub"]))
    return _org_summaries(memberships)


@router.post("/switch-org/{org_id}", response_model=TokenResponse)
async def switch_org(
    org_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Issue a new token with the chosen org as context.
    The user must already be a member of that org.
    """
    payload = TokenService.verify_access_token(
        TokenService.get_token_from_header(authorization)
    )
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = UUID(payload["sub"])
    m = await db.execute(
        select(UserOrganization).where(
            UserOrganization.user_id == user_id,
            UserOrganization.org_id == org_id,
        )
    )
    if not m.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You are not a member of this organization")

    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token, refresh_token = await _issue_tokens(db, user, org_id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.patch("/default-org/{org_id}")
async def set_default_org(
    org_id: UUID,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Set the user's default organization."""
    payload = TokenService.verify_access_token(
        TokenService.get_token_from_header(authorization)
    )
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    success, error = await UserService.set_default_org(db, UUID(payload["sub"]), org_id)
    if not success:
        raise HTTPException(status_code=400, detail=error)
    return {"message": "Default organization updated"}


@router.post("/accept-invite")
@limiter.limit("10/minute")
async def accept_invite(
    request: Request,
    body: OrgInviteAccept,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Accept an org invite using the token from the invite email."""
    payload = TokenService.verify_access_token(
        TokenService.get_token_from_header(authorization)
    )
    if not payload:
        raise HTTPException(status_code=401, detail="Must be logged in to accept an invite")

    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    result = await db.execute(
        select(OrgInvite).where(
            OrgInvite.token_hash == token_hash,
            OrgInvite.accepted_at.is_(None),
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid or already-used invite token")
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invite has expired")

    user_id = UUID(payload["sub"])

    # Validate email matches
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or user.email.lower() != invite.invited_email.lower():
        raise HTTPException(status_code=403, detail="This invite was sent to a different email address")

    is_first = len(await UserService.get_user_memberships(db, user_id)) == 0
    _, error = await UserService.add_user_to_org(
        db, user_id, invite.org_id, role=invite.role, set_default=is_first
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    invite.accepted_at = datetime.utcnow()
    await db.commit()
    return {"message": "You have joined the organization", "org_id": str(invite.org_id)}


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db_session),
):
    payload = TokenService.verify_refresh_token(token_data.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = UUID(payload.get("sub"))
    org_id_raw = payload.get("org_id")
    org_id = UUID(org_id_raw) if org_id_raw else None

    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_hash = TokenService.hash_token(token_data.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
        )
    )
    db_token = result.scalar_one_or_none()
    if not db_token or db_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    roles = await UserService.get_user_roles(db, user.id)
    new_access_token = TokenService.create_access_token(user.id, org_id, roles)
    new_refresh_token = TokenService.create_refresh_token(user.id, org_id)

    db_token.is_revoked = True
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=TokenService.hash_token(new_refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/token/verify", response_model=TokenVerifyResponse)
async def verify_token(token_data: TokenVerifyRequest):
    payload = TokenService.verify_access_token(token_data.token)
    if not payload:
        return TokenVerifyResponse(valid=False)
    org_id_raw = payload.get("org_id")
    return TokenVerifyResponse(
        valid=True,
        user_id=UUID(payload.get("sub")),
        organization_id=UUID(org_id_raw) if org_id_raw else None,
        roles=payload.get("roles", []),
    )


@router.post("/token/revoke")
async def revoke_token(
    token_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db_session),
):
    token_hash = TokenService.hash_token(token_data.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    db_token = result.scalar_one_or_none()
    if not db_token:
        raise HTTPException(status_code=401, detail="Token not found")
    db_token.is_revoked = True
    await db.commit()
    return {"message": "Token revoked successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    token = TokenService.get_token_from_header(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    payload = TokenService.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await UserService.get_user_by_id(db, UUID(payload.get("sub")))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    token = TokenService.get_token_from_header(authorization)
    payload = TokenService.verify_access_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await UserService.get_user_by_id(db, UUID(payload.get("sub")))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.password_hash:
        raise HTTPException(status_code=400, detail="Cannot change password for SSO users")
    if not UserService.verify_password(password_data.old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect current password")

    success, error = await UserService.update_password(db, user.id, password_data.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=error or "Failed to update password")
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Request a password reset link. Email-only, no org required."""
    user = await UserService.get_user_by_email(db, str(body.email))

    if user is not None and user.password_hash is not None:
        # Invalidate old tokens
        old_tokens = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.is_used.is_(False),
            )
        )
        for t in old_tokens.scalars().all():
            t.is_used = True

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        ))
        await db.commit()

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        await send_password_reset_email(
            to_email=str(user.email),
            reset_link=reset_link,
            org_name="",
        )

    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.get("/reset-password/verify/{token}", response_model=ResetPasswordVerifyResponse)
async def verify_reset_token(token: str, db: AsyncSession = Depends(get_db_session)):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used.is_(False),
        )
    )
    db_token = result.scalar_one_or_none()
    if not db_token or db_token.expires_at < datetime.utcnow():
        return ResetPasswordVerifyResponse(valid=False, message="This reset link is invalid or has expired.")

    user_result = await db.execute(select(User).where(User.id == db_token.user_id))
    user = user_result.scalar_one_or_none()
    return ResetPasswordVerifyResponse(valid=True, email=str(user.email) if user else None)


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used.is_(False),
        )
    )
    db_token = result.scalar_one_or_none()
    if not db_token or db_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    db_token.is_used = True
    success, error = await UserService.update_password(db, db_token.user_id, body.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=error or "Failed to reset password.")
    await db.commit()
    return {"message": "Password reset successfully. You can now log in with your new password."}
