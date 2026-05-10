"""Admin endpoints — audit logs, org-level admin actions."""
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database import get_db_session
from models import AuditLog
from schemas import AuditLogResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(authorization: str, org_id: UUID) -> dict:
    """Returns user_info or raises 401/403."""
    info = AuthService.verify_and_get_user(authorization)
    if not info:
        raise HTTPException(status_code=401, detail="Authentication required")
    return info


@router.get("/orgs/{org_id}/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    org_id: UUID,
    authorization: str = Header(...),
    action: Optional[str] = Query(default=None),
    user_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Query audit logs for an organization.
    Only owners and admins can access audit logs.
    """
    info = _require_admin(authorization, org_id)
    user_uuid = UUID(info["user_id"])

    is_super = await AuthService.is_super_user(db, info["user_id"], info.get("org_id"))
    is_admin = await AuthService.is_org_admin(db, info["user_id"], org_id)
    if not is_super and not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required to view audit logs")

    q = select(AuditLog).where(AuditLog.org_id == org_id)
    if action:
        q = q.where(AuditLog.action == action)
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    if status:
        q = q.where(AuditLog.status == status)
    if from_date:
        q = q.where(AuditLog.created_at >= from_date)
    if to_date:
        q = q.where(AuditLog.created_at <= to_date)

    q = q.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)

    result = await db.execute(q)
    logs = result.scalars().all()
    return [
        AuditLogResponse(
            id=str(log.id),
            org_id=str(log.org_id) if log.org_id else None,
            user_id=str(log.user_id) if log.user_id else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            ip_address=log.ip_address,
            status=log.status,
            details=log.details,
            created_at=log.created_at,
        )
        for log in logs
    ]
