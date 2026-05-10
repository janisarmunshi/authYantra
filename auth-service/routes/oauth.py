"""
OAuth 2.0 Authorization Server + OIDC endpoints.

Supported flows:
  • Authorization Code (+ PKCE)
  • Client Credentials
  • Refresh Token

OIDC:
  • /.well-known/openid-configuration
  • /.well-known/jwks.json
  • /oauth/userinfo
  • /oauth/introspect
  • /oauth/revoke
"""
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import get_settings
from database import get_db_session
from models import OAuth2AuthCode, RegisteredApp, RefreshToken, User, UserOrganization
from services.auth_service import AuthService
from services.token_service import TokenService
from services.user_service import UserService

router = APIRouter(tags=["oauth", "oidc"])
settings = get_settings()
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

STANDARD_SCOPES = {"openid", "profile", "email", "offline_access"}
CODE_EXPIRE_SECONDS = 600   # 10 minutes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _verify_pkce(verifier: str, challenge: str, method: str) -> bool:
    if method == "S256":
        digest = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return digest == challenge
    return verifier == challenge   # plain


async def _get_app_by_client_id(db: AsyncSession, client_id: str) -> Optional[RegisteredApp]:
    r = await db.execute(
        select(RegisteredApp).where(
            RegisteredApp.client_id == client_id,
            RegisteredApp.is_active == True,
        )
    )
    return r.scalar_one_or_none()


def _build_id_token(user: User, org_id: Optional[UUID], nonce: Optional[str], client_id: str) -> str:
    """Build a minimal OIDC ID token (HS256 for now)."""
    claims: dict = {
        "iss": settings.FRONTEND_URL,
        "sub": str(user.id),
        "aud": client_id,
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "email": user.email,
        "email_verified": user.email_verified if hasattr(user, "email_verified") else False,
        "name": user.display_name or user.username or user.email,
    }
    if org_id:
        claims["org_id"] = str(org_id)
    if nonce:
        claims["nonce"] = nonce
    return TokenService._create_token(claims, timedelta(hours=1))


# ---------------------------------------------------------------------------
# OIDC Discovery
# ---------------------------------------------------------------------------

@router.get("/.well-known/openid-configuration", include_in_schema=False)
async def openid_configuration(request: Request):
    base = str(request.base_url).rstrip("/")
    return JSONResponse({
        "issuer": base,
        "authorization_endpoint": f"{base}/oauth/authorize",
        "token_endpoint": f"{base}/oauth/token",
        "userinfo_endpoint": f"{base}/oauth/userinfo",
        "jwks_uri": f"{base}/.well-known/jwks.json",
        "introspection_endpoint": f"{base}/oauth/introspect",
        "revocation_endpoint": f"{base}/oauth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["HS256"],
        "scopes_supported": list(STANDARD_SCOPES),
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        "claims_supported": ["sub", "iss", "aud", "exp", "iat", "email", "email_verified", "name", "org_id"],
        "code_challenge_methods_supported": ["S256", "plain"],
    })


@router.get("/.well-known/jwks.json", include_in_schema=False)
async def jwks():
    """
    For HS256 we cannot expose a JWKS (symmetric key).
    Return an empty key set; resource servers must use /oauth/introspect.
    """
    return JSONResponse({"keys": []})


# ---------------------------------------------------------------------------
# Authorization endpoint  GET /oauth/authorize
# ---------------------------------------------------------------------------

@router.get("/oauth/authorize")
async def authorize(
    request: Request,
    client_id: str,
    redirect_uri: str,
    response_type: str = "code",
    scope: str = "openid profile email",
    state: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = "S256",
    nonce: Optional[str] = None,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Issues an authorization code after verifying the client and user session.
    The user must be authenticated (Bearer token in Authorization header).
    In a real deployment the UI would show a consent screen.
    """
    # Validate client
    app = await _get_app_by_client_id(db, client_id)
    if not app:
        raise HTTPException(status_code=400, detail="Unknown client_id")
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Only response_type=code is supported")
    if redirect_uri not in (app.redirect_uris or []):
        raise HTTPException(status_code=400, detail="redirect_uri not registered")
    if "authorization_code" not in (app.allowed_grant_types or []):
        raise HTTPException(status_code=400, detail="Grant type not allowed for this client")

    # Authenticate the user
    if not authorization:
        raise HTTPException(status_code=401, detail="User must be authenticated")
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = UUID(user_info["user_id"])
    org_id_str = user_info.get("org_id")
    org_id = UUID(org_id_str) if org_id_str else None

    # Generate code
    raw_code = secrets.token_urlsafe(32)
    code_hash = _hash_code(raw_code)

    entry = OAuth2AuthCode(
        app_id=app.id,
        user_id=user_id,
        org_id=org_id or app.organization_id,
        code_hash=code_hash,
        redirect_uri=redirect_uri,
        scopes=scope.split(),
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        nonce=nonce,
        expires_at=datetime.utcnow() + timedelta(seconds=CODE_EXPIRE_SECONDS),
    )
    db.add(entry)
    await db.commit()

    params = {"code": raw_code}
    if state:
        params["state"] = state
    return RedirectResponse(f"{redirect_uri}?{urlencode(params)}", status_code=302)


# ---------------------------------------------------------------------------
# Token endpoint  POST /oauth/token
# ---------------------------------------------------------------------------

@router.post("/oauth/token")
async def token(
    request: Request,
    grant_type: str = Form(...),
    code: Optional[str] = Form(default=None),
    redirect_uri: Optional[str] = Form(default=None),
    client_id: Optional[str] = Form(default=None),
    client_secret: Optional[str] = Form(default=None),
    refresh_token: Optional[str] = Form(default=None),
    code_verifier: Optional[str] = Form(default=None),
    scope: Optional[str] = Form(default=None),
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    # Support HTTP Basic Auth for client authentication
    if authorization and authorization.lower().startswith("basic "):
        try:
            decoded = base64.b64decode(authorization[6:]).decode()
            client_id, client_secret = decoded.split(":", 1)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid Basic auth")

    if not client_id:
        raise HTTPException(status_code=400, detail="client_id required")

    app = await _get_app_by_client_id(db, client_id)
    if not app:
        raise HTTPException(status_code=401, detail="Unknown client_id")

    # Verify client secret for confidential clients
    if app.is_confidential:
        if not client_secret:
            raise HTTPException(status_code=401, detail="client_secret required")
        if not app.client_secret_hash or not _pwd.verify(client_secret, app.client_secret_hash):
            raise HTTPException(status_code=401, detail="Invalid client_secret")

    # ── Authorization Code ────────────────────────────────────────────
    if grant_type == "authorization_code":
        if not code:
            raise HTTPException(status_code=400, detail="code required")

        code_hash = _hash_code(code)
        result = await db.execute(
            select(OAuth2AuthCode).where(
                OAuth2AuthCode.code_hash == code_hash,
                OAuth2AuthCode.app_id == app.id,
            )
        )
        auth_code = result.scalar_one_or_none()
        if not auth_code:
            raise HTTPException(status_code=400, detail="Invalid or expired code")
        if auth_code.used_at:
            raise HTTPException(status_code=400, detail="Code already used")
        if auth_code.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Code expired")
        if auth_code.redirect_uri != redirect_uri:
            raise HTTPException(status_code=400, detail="redirect_uri mismatch")

        # PKCE verification
        if auth_code.code_challenge:
            if not code_verifier:
                raise HTTPException(status_code=400, detail="code_verifier required")
            if not _verify_pkce(code_verifier, auth_code.code_challenge, auth_code.code_challenge_method or "S256"):
                raise HTTPException(status_code=400, detail="PKCE verification failed")

        # Mark code used
        auth_code.used_at = datetime.utcnow()

        # Load user
        user_result = await db.execute(select(User).where(User.id == auth_code.user_id))
        user = user_result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(status_code=400, detail="User not found or inactive")

        roles = await UserService.get_user_roles(db, user.id)
        access_tok = TokenService.create_access_token(user.id, auth_code.org_id, roles)
        refresh_tok = TokenService.create_refresh_token(user.id, auth_code.org_id)

        db.add(RefreshToken(
            user_id=user.id,
            token_hash=TokenService.hash_token(refresh_tok),
            expires_at=datetime.utcnow() + timedelta(seconds=app.refresh_token_lifetime),
        ))
        await db.commit()

        scopes = auth_code.scopes or []
        id_token = None
        if "openid" in scopes:
            id_token = _build_id_token(user, auth_code.org_id, auth_code.nonce, client_id)

        return JSONResponse({
            "access_token": access_tok,
            "token_type": "Bearer",
            "expires_in": app.access_token_lifetime,
            "refresh_token": refresh_tok,
            "scope": " ".join(scopes),
            **({"id_token": id_token} if id_token else {}),
        })

    # ── Client Credentials ────────────────────────────────────────────
    elif grant_type == "client_credentials":
        if "client_credentials" not in (app.allowed_grant_types or []):
            raise HTTPException(status_code=400, detail="Grant type not allowed")

        # Issue a token scoped to the app's org, no user subject
        access_tok = TokenService.create_access_token(
            app.organization_id, app.organization_id, ["service"]
        )
        return JSONResponse({
            "access_token": access_tok,
            "token_type": "Bearer",
            "expires_in": app.access_token_lifetime,
        })

    # ── Refresh Token ─────────────────────────────────────────────────
    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token required")

        token_hash = TokenService.hash_token(refresh_token)
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,
            )
        )
        rt = result.scalar_one_or_none()
        if not rt or rt.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid or expired refresh token")

        payload = TokenService.verify_refresh_token(refresh_token)
        if not payload:
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        user_id = UUID(payload["sub"])
        org_id_raw = payload.get("org_id")
        org_id = UUID(org_id_raw) if org_id_raw else None

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(status_code=400, detail="User not found")

        # Rotate tokens
        rt.is_revoked = True
        roles = await UserService.get_user_roles(db, user_id)
        new_access = TokenService.create_access_token(user_id, org_id, roles)
        new_refresh = TokenService.create_refresh_token(user_id, org_id)
        db.add(RefreshToken(
            user_id=user_id,
            token_hash=TokenService.hash_token(new_refresh),
            expires_at=datetime.utcnow() + timedelta(seconds=app.refresh_token_lifetime),
        ))
        await db.commit()

        return JSONResponse({
            "access_token": new_access,
            "token_type": "Bearer",
            "expires_in": app.access_token_lifetime,
            "refresh_token": new_refresh,
        })

    raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {grant_type}")


# ---------------------------------------------------------------------------
# UserInfo  GET /oauth/userinfo
# ---------------------------------------------------------------------------

@router.get("/oauth/userinfo")
@router.post("/oauth/userinfo")
async def userinfo(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db_session),
):
    user_info = AuthService.verify_and_get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_result = await db.execute(
        select(User).where(User.id == UUID(user_info["user_id"]))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return JSONResponse({
        "sub": str(user.id),
        "email": user.email,
        "email_verified": user.email_verified if hasattr(user, "email_verified") else False,
        "name": user.display_name or user.username or user.email,
        "preferred_username": user.username,
        "org_id": user_info.get("org_id"),
    })


# ---------------------------------------------------------------------------
# Introspection  POST /oauth/introspect
# ---------------------------------------------------------------------------

@router.post("/oauth/introspect")
async def introspect(
    token: str = Form(...),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    app = await _get_app_by_client_id(db, client_id)
    if not app:
        raise HTTPException(status_code=401, detail="Unknown client_id")
    if app.is_confidential and (not client_secret or not _pwd.verify(client_secret, app.client_secret_hash or "")):
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    payload = TokenService.verify_access_token(token)
    if not payload:
        return JSONResponse({"active": False})

    return JSONResponse({
        "active": True,
        "sub": payload.get("sub"),
        "org_id": payload.get("org_id"),
        "roles": payload.get("roles", []),
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
        "token_type": "access_token",
    })


# ---------------------------------------------------------------------------
# Revocation  POST /oauth/revoke
# ---------------------------------------------------------------------------

@router.post("/oauth/revoke")
async def revoke(
    token: str = Form(...),
    client_id: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
):
    app = await _get_app_by_client_id(db, client_id)
    if not app:
        raise HTTPException(status_code=401, detail="Unknown client_id")

    token_hash = TokenService.hash_token(token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.is_revoked = True
        await db.commit()

    # Always return 200 per RFC 7009
    return Response(status_code=200)
