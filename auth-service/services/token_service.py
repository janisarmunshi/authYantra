import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
from jose import JWTError, jwt
from config import get_settings

settings = get_settings()


class TokenService:
    """Service for handling JWT tokens"""

    @staticmethod
    def create_access_token(user_id: UUID, organization_id: UUID, roles: list) -> str:
        """Create access token"""
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return TokenService._create_token(
            data={
                "sub": str(user_id),
                "org_id": str(organization_id),
                "roles": roles,
                "type": "access",
            },
            expires_delta=expires_delta,
        )

    @staticmethod
    def create_refresh_token(user_id: UUID, organization_id: UUID) -> str:
        """Create refresh token"""
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        return TokenService._create_token(
            data={
                "sub": str(user_id),
                "org_id": str(organization_id),
                "type": "refresh",
            },
            expires_delta=expires_delta,
        )

    @staticmethod
    def _create_token(data: Dict[str, Any], expires_delta: timedelta) -> str:
        """Internal method to create tokens"""
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode token"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify access token specifically"""
        payload = TokenService.verify_token(token)
        if payload is None:
            return None
        if payload.get("type") != "access":
            return None
        return payload

    @staticmethod
    def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify refresh token specifically"""
        payload = TokenService.verify_token(token)
        if payload is None:
            return None
        if payload.get("type") != "refresh":
            return None
        return payload

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash token for storage in database"""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def get_token_from_header(authorization: str) -> Optional[str]:
        """Extract token from Authorization header"""
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None
