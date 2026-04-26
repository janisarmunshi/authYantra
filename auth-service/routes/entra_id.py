from fastapi import APIRouter, Depends, HTTPException, Header, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import Optional
from database import get_db_session
from services.entra_id_service import EntraIDService
from services.token_service import TokenService
from schemas import (
    TokenResponse,
    UserResponse,
)
from config import get_settings
from models import EntraIDSession

settings = get_settings()
router = APIRouter(prefix="/auth/entra", tags=["entra_id"])


class EntraIDLoginRequest:
    """Request model for starting Entra ID login"""

    def __init__(self, organization_id: UUID, redirect_uri: str, link_account: bool = False):
        self.organization_id = organization_id
        self.redirect_uri = redirect_uri
        self.link_account = link_account


class EntraIDLoginResponse:
    """Response model for Entra ID login URL"""

    def __init__(self, authorization_url: str, state: str):
        self.authorization_url = authorization_url
        self.state = state


class LinkAccountRequest:
    """Request model for linking Entra ID account"""

    def __init__(self, entra_id: str):
        self.entra_id = entra_id


@router.get("/authorize")
async def authorize_entra(
    organization_id: UUID,
    redirect_uri: str,
    link_account: bool = False,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Start Entra ID OAuth 2.0 authorization code flow.

    Query Parameters:
    - organization_id: UUID of the organization
    - redirect_uri: URI to redirect to after authorization (must be registered)
    - link_account: Whether this is for linking an existing account (default: false)

    Returns:
    - authorization_url: URL to redirect user to for Entra ID login
    - state: CSRF protection token (for verification)
    """
    auth_url, state, error = await EntraIDService.generate_authorization_url(
        db=db,
        organization_id=organization_id,
        redirect_uri=redirect_uri,
        link_account=link_account,
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    return {"authorization_url": auth_url, "state": state}


@router.get("/callback")
async def entra_callback_get(
    code: str,
    state: str,
    organization_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle OAuth 2.0 callback from Entra ID (GET method for query response_mode).
    """
    return await _process_entra_callback(db, code, state, organization_id)


@router.post("/callback")
async def entra_callback_post(
    code: str = Form(...),
    state: str = Form(...),
    organization_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle OAuth 2.0 callback from Entra ID (POST method for form_post response_mode).
    
    When response_mode=form_post is used in Azure configuration, the callback data
    is sent as form data in a POST request instead of query parameters.
    
    Form Parameters:
    - code: Authorization code from Entra ID
    - state: CSRF protection token (must match what was stored)
    - organization_id: [Optional] Organization UUID as string (looked up from state if not provided)

    Returns:
    - access_token: JWT token for authenticated requests
    - refresh_token: Token to refresh expired access tokens
    - token_type: Always "bearer"
    - expires_in: Token expiration time in seconds
    - redirect_uri: Original redirect URI to send user back to their app
    """
    org_id = UUID(organization_id) if organization_id else None
    return await _process_entra_callback(db, code, state, org_id)


async def _process_entra_callback(db: AsyncSession, code: str, state: str, organization_id: Optional[UUID]):
    """
    Process Entra ID callback - shared logic for both GET and POST methods.
    If organization_id is not provided, it will be looked up from the state token.
    """
    # Store to check password
    entra_session = None
    
    # If organization_id not provided, we need to look up the state first to find it
    # Try to find the session - first without organization_id
    if organization_id:
        session_result = await db.execute(
            select(EntraIDSession).where(
                and_(
                    EntraIDSession.state == state,
                    EntraIDSession.organization_id == organization_id,
                )
            )
        )
        entra_session = session_result.scalar_one_or_none()
    else:
        # Look up by state only - there should be one session per state
        session_result = await db.execute(
            select(EntraIDSession).where(
                EntraIDSession.state == state,
            )
        )
        entra_session = session_result.scalar_one_or_none()
        if entra_session:
            organization_id = entra_session.organization_id
    
    if not entra_session:
        raise HTTPException(status_code=401, detail="Invalid or expired state")
    
    # Exchange code for user info
    user_info, error = await EntraIDService.exchange_code(db, organization_id, code, state)

    if error:
        raise HTTPException(status_code=401, detail=error)

    if not user_info:
        raise HTTPException(status_code=401, detail="Could not authenticate with Entra ID")

    # Get or create user
    user, error = await EntraIDService.get_or_create_entra_user(
        db=db,
        organization_id=organization_id,
        email=user_info["email"],
        entra_id=user_info["id"],
        name=user_info.get("name"),
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    if not user:
        raise HTTPException(status_code=500, detail="Could not create or retrieve user")

    # Create JWT tokens
    access_token, refresh_token, error = await EntraIDService.create_tokens_for_entra_user(db, user)

    if error:
        raise HTTPException(status_code=500, detail=error)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "redirect_uri": entra_session.redirect_uri,  # Include redirect URI for app
        "email": user_info["email"],  # User's email from Microsoft
        "name": user_info.get("name"),  # User's display name from Microsoft
        "user_id": str(user.id),  # Internal user ID
        "organization_id": str(organization_id),  # Organization ID
    }


@router.post("/link-account")
async def link_account(
    entra_id: str,
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Link an existing local user account to Entra ID.

    Required Headers:
    - Authorization: Bearer {access_token}

    Request Body:
    - entra_id: The Entra ID object ID from Microsoft Graph

    Returns:
    - message: Success confirmation
    """
    # Verify access token
    token = TokenService.get_token_from_header(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    payload = TokenService.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = UUID(payload.get("sub"))
    organization_id = UUID(payload.get("org_id"))

    # Link Entra ID to user
    success, error = await EntraIDService.link_entra_id(db, user_id, entra_id, organization_id)

    if not success:
        raise HTTPException(status_code=400, detail=error)

    return {"message": "Account linked successfully"}


@router.post("/unlink-account")
async def unlink_account(
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Remove Entra ID link from user account.

    Required Headers:
    - Authorization: Bearer {access_token}

    Returns:
    - message: Success confirmation
    """
    # Verify access token
    token = TokenService.get_token_from_header(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    payload = TokenService.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = UUID(payload.get("sub"))
    organization_id = UUID(payload.get("org_id"))

    # Unlink Entra ID from user
    success, error = await EntraIDService.unlink_entra_id(db, user_id, organization_id)

    if not success:
        raise HTTPException(status_code=400, detail=error)

    return {"message": "Account unlinked successfully"}
