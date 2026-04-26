import secrets
import hashlib
import base64
import httpx
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from uuid import UUID
from urllib.parse import quote
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import get_settings
from models import EntraIDSession, User, Organization
from services.user_service import UserService
from services.token_service import TokenService

settings = get_settings()


class EntraIDService:
    """Service for Microsoft Entra ID OAuth 2.0 authentication"""

    @staticmethod
    def _generate_pkce_pair() -> Tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("utf-8")).digest()
        ).decode("utf-8").rstrip("=")
        return code_verifier, code_challenge

    @staticmethod
    def _generate_state() -> str:
        """Generate CSRF protection state token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    async def generate_authorization_url(
        db: AsyncSession,
        organization_id: UUID,
        redirect_uri: str,
        link_account: bool = False,
        user_id: Optional[UUID] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Generate Entra ID authorization URL with PKCE.
        Returns: (authorization_url, state, error)
        """
        try:
            # Verify organization exists and has Entra ID configured
            result = await db.execute(
                select(Organization).where(Organization.id == organization_id)
            )
            org = result.scalar_one_or_none()

            if not org:
                return None, None, "Organization not found"

            if not org.entra_id_tenant_id or not org.entra_id_client_id:
                return None, None, "Organization not configured for Entra ID"

            # Generate PKCE pair
            code_verifier, code_challenge = EntraIDService._generate_pkce_pair()
            state = EntraIDService._generate_state()

            # Store session in database
            expires_at = datetime.utcnow() + timedelta(seconds=settings.OAUTH_STATE_EXPIRY)

            db_session = EntraIDSession(
                organization_id=organization_id,
                state=state,
                code_verifier=code_verifier,
                redirect_uri=redirect_uri,  # Store the redirect URI for later
                user_id=user_id,  # For account linking
                expires_at=expires_at,
            )

            db.add(db_session)
            await db.commit()

            # Build authorization URL with proper URL encoding
            auth_url = (
                f"{settings.ENTRA_ID_AUTHORITY}/{org.entra_id_tenant_id}/oauth2/v2.0/authorize?"
                f"client_id={quote(org.entra_id_client_id, safe='')}&"
                f"redirect_uri={quote(redirect_uri, safe='')}&"
                f"response_type={settings.ENTRA_ID_RESPONSE_TYPE}&"
                f"scope={quote(settings.ENTRA_ID_SCOPE, safe='')}&"
                f"state={state}&"
                f"code_challenge={code_challenge}&"
                f"code_challenge_method=S256"
            )
            
            # Add response_mode only if configured
            if settings.ENTRA_ID_RESPONSE_MODE:
                auth_url += f"&response_mode={settings.ENTRA_ID_RESPONSE_MODE}"

            return auth_url, state, None

        except Exception as e:
            await db.rollback()
            return None, None, f"Error generating authorization URL: {str(e)}"

    @staticmethod
    async def exchange_code(
        db: AsyncSession,
        organization_id: UUID,
        code: str,
        state: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Exchange authorization code for Entra ID tokens.
        Returns: (user_info dict with email/oid, error)
        """
        try:
            # Verify organization
            result = await db.execute(
                select(Organization).where(Organization.id == organization_id)
            )
            org = result.scalar_one_or_none()

            if not org:
                return None, "Organization not found"

            # Verify state exists and is not expired
            session_result = await db.execute(
                select(EntraIDSession).where(
                    EntraIDSession.state == state,
                    EntraIDSession.organization_id == organization_id,
                )
            )
            session = session_result.scalar_one_or_none()

            if not session:
                return None, "Invalid or expired state"

            if session.expires_at < datetime.utcnow():
                # Delete expired session
                await db.delete(session)
                await db.commit()
                return None, "State has expired"

            # Exchange code for tokens
            token_url = f"{settings.ENTRA_ID_AUTHORITY}/{org.entra_id_tenant_id}/oauth2/v2.0/token"

            async with httpx.AsyncClient() as client:
                # Handle client secret as bytes or string
                client_secret = org.entra_id_client_secret
                if isinstance(client_secret, bytes):
                    client_secret = client_secret.decode('utf-8')
                
                token_response = await client.post(
                    token_url,
                    data={
                        "client_id": org.entra_id_client_id,
                        "client_secret": client_secret,
                        "code": code,
                        "redirect_uri": session.redirect_uri,  # REQUIRED: Must match the authorization request
                        "code_verifier": session.code_verifier,
                        "grant_type": "authorization_code",
                        "scope": settings.ENTRA_ID_SCOPE,
                    },
                    timeout=10,
                )

                if token_response.status_code != 200:
                    error = token_response.json().get("error_description", "Token exchange failed")
                    return None, f"Entra ID error: {error}"

                tokens = token_response.json()
                access_token = tokens.get("access_token")

            if not access_token:
                return None, "No access token received from Entra ID"

            # Get user info from Microsoft Graph
            user_info = await EntraIDService._get_user_info(access_token)

            if not user_info:
                return None, "Could not retrieve user information from Entra ID"

            # Clean up used session
            await db.delete(session)
            await db.commit()

            return user_info, None

        except Exception as e:
            await db.rollback()
            return None, f"Error exchanging code: {str(e)}"

    @staticmethod
    async def _get_user_info(access_token: str) -> Optional[Dict[str, Any]]:
        """Get user info from Microsoft Graph API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "id": data.get("id"),  # Entra ID object ID
                        "email": data.get("userPrincipalName") or data.get("mail"),
                        "name": data.get("displayName"),
                    }
                return None

        except Exception:
            return None

    @staticmethod
    async def get_or_create_entra_user(
        db: AsyncSession,
        organization_id: UUID,
        email: str,
        entra_id: str,
        name: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Get or create user for Entra ID authentication.
        Returns: (user object, error)
        """
        try:
            # Check if user exists by entra_id
            result = await db.execute(
                select(User).where(
                    User.entra_id == entra_id,
                    User.organization_id == organization_id,
                )
            )
            user = result.scalar_one_or_none()

            if user:
                return user, None

            # Check if user exists by email
            result = await db.execute(
                select(User).where(
                    User.email == email,
                    User.organization_id == organization_id,
                )
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                # User exists locally - update with Entra ID
                if not existing_user.entra_id:
                    existing_user.entra_id = entra_id
                    await db.commit()
                    await db.refresh(existing_user)
                return existing_user, None

            # Create new user
            new_user = User(
                organization_id=organization_id,
                email=email,
                entra_id=entra_id,
                username=name or email.split("@")[0],  # Generate username from email
                is_active=True,
            )

            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)

            return new_user, None

        except Exception as e:
            await db.rollback()
            return None, f"Error creating/retrieving user: {str(e)}"

    @staticmethod
    async def create_tokens_for_entra_user(
        db: AsyncSession,
        user: User,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Create JWT tokens for authenticated Entra ID user.
        Returns: (access_token, refresh_token, error)
        """
        try:
            # Get user roles
            roles = await UserService.get_user_roles(db, user.id)

            # Create tokens
            access_token = TokenService.create_access_token(user.id, user.organization_id, roles)
            refresh_token = TokenService.create_refresh_token(user.id, user.organization_id)

            # Store refresh token hash
            from models import RefreshToken

            token_hash = TokenService.hash_token(refresh_token)
            expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

            db_refresh_token = RefreshToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )

            db.add(db_refresh_token)
            await db.commit()

            return access_token, refresh_token, None

        except Exception as e:
            await db.rollback()
            return None, None, f"Error creating tokens: {str(e)}"

    @staticmethod
    async def link_entra_id(
        db: AsyncSession,
        user_id: UUID,
        entra_id: str,
        organization_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """
        Link Entra ID to existing local user account.
        Returns: (success, error)
        """
        try:
            # Get user
            user = await UserService.get_user_by_id(db, user_id, organization_id)

            if not user:
                return False, "User not found"

            # Check if Entra ID already linked to another user
            result = await db.execute(
                select(User).where(
                    User.entra_id == entra_id,
                    User.organization_id == organization_id,
                    User.id != user_id,
                )
            )

            if result.scalar_one_or_none():
                return False, "This Entra ID is already linked to another account"

            # Link Entra ID
            user.entra_id = entra_id
            await db.commit()

            return True, None

        except Exception as e:
            await db.rollback()
            return False, f"Error linking account: {str(e)}"

    @staticmethod
    async def unlink_entra_id(
        db: AsyncSession,
        user_id: UUID,
        organization_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """
        Remove Entra ID link from user account.
        Returns: (success, error)
        """
        try:
            # Get user
            user = await UserService.get_user_by_id(db, user_id, organization_id)

            if not user:
                return False, "User not found"

            if not user.entra_id:
                return False, "This account is not linked to Entra ID"

            # Unlink
            user.entra_id = None
            await db.commit()

            return True, None

        except Exception as e:
            await db.rollback()
            return False, f"Error unlinking account: {str(e)}"
