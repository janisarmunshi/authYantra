"""Structured audit logging — write-only, never mutated."""
import logging
from typing import Optional, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:

    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        *,
        status: str = "success",
        org_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """
        Append an audit record to the session.
        Caller is responsible for committing.
        Errors are swallowed so audit logging never breaks the main flow.
        """
        try:
            entry = AuditLog(
                org_id=org_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                details=details,
            )
            db.add(entry)
        except Exception as exc:
            logger.warning("audit_log failed for action=%s: %s", action, exc)

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    @staticmethod
    async def log_login(
        db: AsyncSession,
        user_id: UUID,
        org_id: Optional[UUID],
        success: bool,
        ip: Optional[str] = None,
        ua: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        await AuditService.log(
            db,
            "user.login",
            status="success" if success else "failure",
            user_id=user_id,
            org_id=org_id,
            resource_type="user",
            resource_id=str(user_id),
            ip_address=ip,
            user_agent=ua,
            details={"reason": reason} if reason else None,
        )

    @staticmethod
    async def log_org_event(
        db: AsyncSession,
        action: str,
        org_id: UUID,
        actor_id: UUID,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        await AuditService.log(
            db,
            action,
            org_id=org_id,
            user_id=actor_id,
            resource_type="org",
            resource_id=resource_id or str(org_id),
            details=details,
        )
