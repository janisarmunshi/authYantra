from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


# ── Organization ──────────────────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    entra_id_tenant_id: Optional[str] = None


class OrganizationEntraIDUpdate(BaseModel):
    entra_id_tenant_id: str = Field(..., min_length=1)
    entra_id_client_id: str = Field(..., min_length=1)
    entra_id_client_secret: str = Field(..., min_length=1)


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    entra_id_tenant_id: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OrgSummary(BaseModel):
    id: str
    name: str
    role: str
    is_default: bool


# ── Membership & Invites ──────────────────────────────────────────────────────

class OrgMemberAdd(BaseModel):
    email: EmailStr
    role: str = Field("member", pattern="^(admin|member)$")


class OrgMemberResponse(BaseModel):
    user_id: str
    email: str
    username: Optional[str]
    role: str
    is_default: bool
    joined_at: datetime


class OrgInviteCreate(BaseModel):
    email: EmailStr
    role: str = Field("member", pattern="^(admin|member)$")


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


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: Optional[str]
    is_active: bool
    organization_id: Optional[UUID]
    created_at: datetime

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
    permissions: dict = Field(default={})


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    permissions: Optional[dict] = None
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    id: UUID
    name: str
    permissions: dict
    is_active: bool

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
    role_id: UUID = Field(..., description="ID of the role to assign")


# ── Registered App ────────────────────────────────────────────────────────────

class RegisteredAppCreate(BaseModel):
    app_name: str = Field(..., min_length=1, max_length=255)
    app_type: str = Field(..., description="web, desktop, or mobile")
    redirect_uris: List[str] = Field(default=[])


class RegisteredAppResponse(BaseModel):
    id: UUID
    app_name: str
    app_type: str
    api_key: str
    redirect_uris: List[str]
    is_active: bool

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
