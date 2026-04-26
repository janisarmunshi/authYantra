import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from database import get_db_session
from schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefreshRequest,
    TokenVerifyRequest,
    TokenVerifyResponse,
    UserResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ResetPasswordVerifyResponse,
)
from services.user_service import UserService
from services.token_service import TokenService
from services.rate_limiter import limiter
from services.email_service import send_password_reset_email
from models import RefreshToken, PasswordResetToken
from sqlalchemy import select
from datetime import datetime, timedelta
from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=dict)
@limiter.limit("10/minute")
async def register(
    request: Request,
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user"""
    user, error = await UserService.register_user(
        db=db,
        organization_id=user_data.organization_id,
        email=user_data.email,
        password=user_data.password,
        username=user_data.username,
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    return {"message": "User registered successfully", "user_id": str(user.id)}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    organization_id: UUID = Header(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db_session),
):
    """Login with email and password"""
    user, error = await UserService.authenticate_user(
        db=db,
        organization_id=organization_id,
        email=credentials.email,
        password=credentials.password,
    )

    if error:
        raise HTTPException(status_code=401, detail=error)

    # Get user roles
    roles = await UserService.get_user_roles(db, user.id)

    # Create tokens
    access_token = TokenService.create_access_token(user.id, user.organization_id, roles)
    refresh_token = TokenService.create_refresh_token(user.id, user.organization_id)

    # Store refresh token hash
    token_hash = TokenService.hash_token(refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(db_refresh_token)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Refresh access token using refresh token"""
    # Verify refresh token
    payload = TokenService.verify_refresh_token(token_data.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Get user and organization
    user_id = UUID(payload.get("sub"))
    organization_id = UUID(payload.get("org_id"))

    user = await UserService.get_user_by_id(db, user_id, organization_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Check if refresh token has been revoked
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

    # Get updated roles
    roles = await UserService.get_user_roles(db, user.id)

    # Create new tokens
    new_access_token = TokenService.create_access_token(user.id, user.organization_id, roles)
    new_refresh_token = TokenService.create_refresh_token(user.id, user.organization_id)

    # Revoke old refresh token and store new one
    db_token.is_revoked = True
    new_token_hash = TokenService.hash_token(new_refresh_token)
    new_expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db_new_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=new_expires_at,
    )
    db.add(db_new_refresh_token)
    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/token/verify", response_model=TokenVerifyResponse)
async def verify_token(
    token_data: TokenVerifyRequest,
):
    """Verify access token validity"""
    payload = TokenService.verify_access_token(token_data.token)

    if not payload:
        return TokenVerifyResponse(valid=False)

    return TokenVerifyResponse(
        valid=True,
        user_id=UUID(payload.get("sub")),
        organization_id=UUID(payload.get("org_id")),
        roles=payload.get("roles", []),
    )


@router.post("/token/revoke")
async def revoke_token(
    token_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Revoke a refresh token (logout)"""
    # Verify token exists
    token_hash = TokenService.hash_token(token_data.refresh_token)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(status_code=401, detail="Token not found")

    # Revoke token
    db_token.is_revoked = True
    await db.commit()

    return {"message": "Token revoked successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Get current authenticated user"""
    token = TokenService.get_token_from_header(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    payload = TokenService.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = UUID(payload.get("sub"))
    organization_id = UUID(payload.get("org_id"))

    user = await UserService.get_user_by_id(db, user_id, organization_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Change user password.
    
    Required Headers:
    - Authorization: Bearer {access_token}
    
    Request body:
    - old_password: Current password
    - new_password: New password (minimum 8 characters)
    
    Returns:
    - message: Success confirmation
    """
    # Verify user and token
    token = TokenService.get_token_from_header(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    payload = TokenService.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = UUID(payload.get("sub"))
    organization_id = UUID(payload.get("org_id"))

    # Get user
    user = await UserService.get_user_by_id(db, user_id, organization_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.password_hash:
        raise HTTPException(
            status_code=400,
            detail="Cannot change password for SSO users. Link a local account first."
        )

    # Verify old password
    success = UserService.verify_password(password_data.old_password, user.password_hash)
    if not success:
        raise HTTPException(status_code=401, detail="Incorrect current password")

    # Update password
    success, error = await UserService.update_password(db, user_id, password_data.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=error or "Failed to update password")

    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,  # required by SlowAPI rate-limiter
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Request a password reset link.

    Always returns 200 regardless of whether the email exists — this prevents
    user-enumeration attacks. The reset link is emailed only if the account is found.
    """
    from models import User, Organization

    user_result = await db.execute(
        select(User).where(
            User.organization_id == body.organization_id,
            User.email == str(body.email),
            User.is_active.is_(True),
        )
    )
    user = user_result.scalar_one_or_none()

    if user is not None and user.password_hash is not None:
        # Invalidate any previous unused tokens for this user
        old_tokens_result = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.is_used.is_(False),
            )
        )
        for old_token in old_tokens_result.scalars().all():
            setattr(old_token, "is_used", True)

        # Generate a cryptographically random token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )

        db_token = PasswordResetToken(
            user_id=user.id,
            organization_id=user.organization_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(db_token)
        await db.commit()

        # Build reset link
        reset_link = (
            f"{settings.FRONTEND_URL}/reset-password"
            f"?token={raw_token}"
            f"&org={body.organization_id}"
        )

        org_result = await db.execute(
            select(Organization).where(Organization.id == body.organization_id)
        )
        org = org_result.scalar_one_or_none()
        org_name: str = str(org.name) if org is not None else ""

        await send_password_reset_email(
            to_email=str(user.email),
            reset_link=reset_link,
            org_name=org_name,
        )

    # Always respond with the same message — never reveal whether email exists
    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.get("/reset-password/verify/{token}", response_model=ResetPasswordVerifyResponse)
async def verify_reset_token(
    token: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Verify that a password reset token is valid and unused.
    Called by the frontend before showing the new-password form.
    """
    from models import User

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used.is_(False),
        )
    )
    db_token = result.scalar_one_or_none()

    if db_token is None:
        return ResetPasswordVerifyResponse(
            valid=False,
            message="This reset link is invalid or has expired.",
        )

    expires_at: datetime = db_token.expires_at  # type: ignore[assignment]
    if expires_at < datetime.utcnow():
        return ResetPasswordVerifyResponse(
            valid=False,
            message="This reset link is invalid or has expired.",
        )

    user_result = await db.execute(
        select(User).where(User.id == db_token.user_id)
    )
    user = user_result.scalar_one_or_none()
    user_email: str | None = str(user.email) if user is not None else None

    return ResetPasswordVerifyResponse(valid=True, email=user_email)


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,  # required by SlowAPI rate-limiter
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Reset password using the one-time token from the reset email.
    The token is invalidated immediately after use.
    """
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used.is_(False),
        )
    )
    db_token = result.scalar_one_or_none()

    if db_token is None:
        raise HTTPException(
            status_code=400,
            detail="This reset link is invalid or has expired. Please request a new one.",
        )

    expires_at: datetime = db_token.expires_at  # type: ignore[assignment]
    if expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="This reset link is invalid or has expired. Please request a new one.",
        )

    # Mark token as used immediately (prevents replay attacks)
    setattr(db_token, "is_used", True)

    # Update the user's password
    user_id: UUID = db_token.user_id  # type: ignore[assignment]
    success, error = await UserService.update_password(db, user_id, body.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=error or "Failed to reset password.")

    await db.commit()
    return {"message": "Password reset successfully. You can now log in with your new password."}

