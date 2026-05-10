"""MFA management endpoints — TOTP setup, verification, status, disable."""
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from schemas import MfaSetupResponse, MfaVerifyRequest, MfaStatusResponse
from services.auth_service import AuthService
from services.mfa_service import MfaService
from services.audit_service import AuditService

router = APIRouter(prefix="/mfa", tags=["mfa"])


def _require_user(authorization: str) -> dict:
    info = AuthService.verify_and_get_user(authorization)
    if not info:
        raise HTTPException(status_code=401, detail="Authentication required")
    return info


@router.post("/totp/setup", response_model=MfaSetupResponse)
async def setup_totp(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Initiate TOTP setup. Returns a provisioning URI + base32 secret.
    The client must call /mfa/totp/verify to activate.
    """
    info = _require_user(authorization)
    user_id = UUID(info["user_id"])

    from sqlalchemy import select
    from models import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cred_id, uri, secret, backup_codes = await MfaService.initiate_totp_setup(
        db, user_id, user.email
    )
    await AuditService.log(
        db, "mfa.totp_setup_initiated",
        user_id=user_id,
        resource_type="mfa",
        resource_id=cred_id,
    )
    await db.commit()

    return MfaSetupResponse(
        credential_id=cred_id,
        totp_uri=uri,
        secret=secret,
        backup_codes=backup_codes,
    )


@router.post("/totp/verify")
async def verify_totp_setup(
    body: MfaVerifyRequest,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Confirm setup with the first TOTP code. Activates MFA on the account."""
    info = _require_user(authorization)
    user_id = UUID(info["user_id"])

    success, error = await MfaService.verify_and_activate_totp(
        db, UUID(body.credential_id), body.code
    )
    if not success:
        raise HTTPException(status_code=400, detail=error or "Verification failed")

    await AuditService.log(
        db, "mfa.totp_activated",
        user_id=user_id,
        resource_type="mfa",
        resource_id=body.credential_id,
    )
    await db.commit()
    return {"message": "MFA activated successfully"}


@router.delete("/disable")
async def disable_mfa(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Disable MFA for the authenticated user."""
    info = _require_user(authorization)
    user_id = UUID(info["user_id"])

    await MfaService.disable_mfa(db, user_id)
    await AuditService.log(
        db, "mfa.disabled",
        user_id=user_id,
        resource_type="mfa",
    )
    await db.commit()
    return {"message": "MFA disabled"}


@router.get("/status", response_model=MfaStatusResponse)
async def mfa_status(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    info = _require_user(authorization)
    status = await MfaService.get_mfa_status(db, UUID(info["user_id"]))
    return MfaStatusResponse(**status)
