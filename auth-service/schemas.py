from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

ROLE_PATTERN = "^(owner|admin|developer|auditor|billing|member)$"

# ── Organization ──────────────────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    mfa_required: Optional[bool] = None
    allowed_email_domains: Optional[List[str]] = None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    entra_id_tenant_id: Optional[str] = None
    entra_id_client_id: Optional[str] = None
    is_active: bool
    mfa_required: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Backwards-compatibility alias
OrganizationEntraIDUpdate = OrganizationUpdate


class OrgSummary(BaseModel):
    id: str
    name: str
    role: str
    is_default: bool


# ── Membership & Invites ──────────────────────────────────────────────────────

class OrgMemberAdd(BaseModel):
    email: EmailStr
    role: str = Field("member", pattern=ROLE_PATTERN)


class OrgMemberResponse(BaseModel):
    user_id: str
    email: str
    username: Optional[str]
    role: str
    is_default: bool
    joined_at: datetime


class OrgInviteCreate(BaseModel):
    email: EmailStr
    role: str = Field("member", pattern=ROLE_PATTERN)


class OrgInviteAccept(BaseModel):
    token: str


class OrgInviteResponse(BaseModel):
    id: str
    invited_email: str
    role: str
    expires_at: datetime
    accepted_at: Optional[datetime]


# ── User ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    username: Optional[str] = Field(None, min_length=3, max_length=255)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None   # TOTP or backup code if MFA is enabled


class UserResponse(BaseModel):
    id: UUID
    email: str
    email_verified: bool
    username: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_locked: bool
    mfa_enabled: bool
    organization_id: Optional[UUID]
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Token ─────────────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    org_id: Optional[str] = None
    needs_org_selection: bool = False
    organizations: List[OrgSummary] = []
    mfa_required: bool = False      # True → client must submit MFA code before receiving tokens
    mfa_token: Optional[str] = None # Short-lived token for the MFA challenge step


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenVerifyRequest(BaseModel):
    token: str


class TokenVerifyResponse(BaseModel):
    valid: bool
    user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    roles: Optional[List[str]] = None


class TokenRevokeRequest(BaseModel):
    refresh_token: str


# ── Role ──────────────────────────────────────────────────────────────────────

class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    permissions: Dict[str, List[str]] = Field(default={})


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    permissions: Optional[Dict[str, List[str]]] = None
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    permissions: Dict[str, List[str]]
    is_active: bool
    is_system: bool

    class Config:
        from_attributes = True


# ── Endpoint ──────────────────────────────────────────────────────────────────

class EndpointRegisterRequest(BaseModel):
    endpoint: str = Field(..., min_length=1)
    actions: List[str] = Field(default=["read", "write", "delete", "modify"])
    description: Optional[str] = Field(None, max_length=500)


class EndpointResponse(BaseModel):
    id: UUID
    endpoint: str
    actions: List[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── User-Role Assignment ──────────────────────────────────────────────────────

class UserRoleAssignRequest(BaseModel):
    role_id: UUID


# ── Registered App ────────────────────────────────────────────────────────────

class RegisteredAppCreate(BaseModel):
    app_name: str = Field(..., min_length=1, max_length=255)
    app_type: str = Field(..., description="web | desktop | mobile | service")
    redirect_uris: List[str] = Field(default=[])
    allowed_scopes: List[str] = Field(default=["openid", "profile", "email"])
    allowed_grant_types: List[str] = Field(default=["authorization_code", "refresh_token"])
    is_confidential: bool = True


class RegisteredAppResponse(BaseModel):
    id: UUID
    app_name: str
    app_type: str
    client_id: Optional[str] = None
    api_key: str
    redirect_uris: List[str] = []
    allowed_scopes: List[str] = []
    allowed_grant_types: List[str] = []
    access_token_lifetime: int = 900
    refresh_token_lifetime: int = 604800
    is_active: bool
    is_confidential: bool = True

    class Config:
        from_attributes = True


# ── Password ──────────────────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class ResetPasswordVerifyResponse(BaseModel):
    valid: bool
    email: Optional[str] = None
    message: Optional[str] = None


# ── MFA ───────────────────────────────────────────────────────────────────────

class MfaSetupResponse(BaseModel):
    """Returned when initiating TOTP setup — client must display the QR code."""
    credential_id: str
    totp_uri: str          # otpauth:// URI for QR code
    secret: str            # base32 secret (show once, user saves it)
    backup_codes: List[str]


class MfaVerifyRequest(BaseModel):
    credential_id: str
    code: str = Field(..., min_length=6, max_length=8)


class MfaChallengeRequest(BaseModel):
    """Submitted to complete login when mfa_required=True in LoginResponse."""
    mfa_token: str         # short-lived token from LoginResponse
    code: str = Field(..., min_length=6, max_length=8)


class MfaStatusResponse(BaseModel):
    enabled: bool
    type: Optional[str]
    last_used_at: Optional[datetime]


# ── Identity Provider ─────────────────────────────────────────────────────────

class IdentityProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., description="google | github | microsoft | saml | oidc | magic_link")
    config: Dict[str, Any] = Field(default={})
    attribute_mapping: Dict[str, str] = Field(default={})
    auto_provision: bool = True
    default_role: str = Field("member", pattern=ROLE_PATTERN)


class IdentityProviderUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    attribute_mapping: Optional[Dict[str, str]] = None
    auto_provision: Optional[bool] = None
    default_role: Optional[str] = Field(None, pattern=ROLE_PATTERN)
    is_active: Optional[bool] = None


class IdentityProviderResponse(BaseModel):
    id: str
    name: str
    type: str
    is_active: bool
    auto_provision: bool
    default_role: str
    created_at: datetime
    updated_at: datetime


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: str
    org_id: Optional[str]
    user_id: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    status: str
    details: Optional[Dict[str, Any]]
    created_at: datetime


# ── OAuth 2.0 ─────────────────────────────────────────────────────────────────

class OAuthTokenRequest(BaseModel):
    """Form-encoded body for POST /oauth/token"""
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    code_verifier: Optional[str] = None   # PKCE
    scope: Optional[str] = None


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None        # OIDC ID token


# ── Entra ID ──────────────────────────────────────────────────────────────────

class EntraIDAuthorizationRequest(BaseModel):
    organization_id: UUID
    redirect_uri: str
    link_account: bool = False


class EntraIDAuthorizationResponse(BaseModel):
    authorization_url: str
    state: str


class EntraIDCallbackRequest(BaseModel):
    code: str
    state: str
    organization_id: UUID


class EntraIDUserInfo(BaseModel):
    id: str
    email: str
    name: Optional[str]


class LinkAccountRequest(BaseModel):
    entra_id: str


class UnlinkAccountRequest(BaseModel):
    pass


class EntraIDLoginResponse(BaseModel):
    message: str


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


# ── Error ─────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
