from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


# Organization Schemas
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    entra_id_tenant_id: Optional[str] = None


class OrganizationEntraIDUpdate(BaseModel):
    """Schema for updating Entra ID configuration for an organization"""
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


# User Schemas
class UserRegister(BaseModel):
    email: EmailStr
    username: Optional[str] = Field(None, min_length=3, max_length=255)
    password: str = Field(..., min_length=8)
    organization_id: UUID


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Token Schemas
class TokenRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


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


# Role Schemas
class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Role name (e.g., 'viewer', 'editor')")
    permissions: dict = Field(
        default={},
        description="Permission mapping: endpoint -> list of allowed actions. Example: {'/api/users': ['read', 'write'], '/api/reports': ['read']}"
    )


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


# Endpoint Schemas
class EndpointRegisterRequest(BaseModel):
    endpoint: str = Field(..., min_length=1, description="API endpoint path, e.g. /api/users")
    actions: List[str] = Field(default=[], description="Allowed actions, e.g. ['read', 'write']")
    description: Optional[str] = None


class EndpointResponse(BaseModel):
    id: UUID
    endpoint: str
    actions: List[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# User-Role Assignment
class UserRoleAssignRequest(BaseModel):
    role_id: UUID


# Registered App Schemas
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


# Error Schemas
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


# Health Check
class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str

# Entra ID OAuth Schemas
class EntraIDAuthorizationRequest(BaseModel):
    organization_id: UUID
    redirect_uri: str
    link_account: bool = Field(False, description="Whether to link to existing account")


class EntraIDAuthorizationResponse(BaseModel):
    authorization_url: str = Field(..., description="URL to redirect user to Entra ID login")
    state: str = Field(..., description="CSRF protection token")


class EntraIDCallbackRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Entra ID")
    state: str = Field(..., description="CSRF protection token")
    organization_id: UUID


class EntraIDUserInfo(BaseModel):
    id: str = Field(..., description="Entra ID object ID")
    email: str
    name: Optional[str]


class LinkAccountRequest(BaseModel):
    entra_id: str = Field(..., description="Entra ID object ID to link")


class UnlinkAccountRequest(BaseModel):
    pass  # Just needs authorization header


class EntraIDLoginResponse(BaseModel):
    message: str


# Change Password Schema
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


# Endpoint Registration Schema
class EndpointRegisterRequest(BaseModel):
    endpoint: str = Field(..., min_length=1, description="API endpoint path (e.g., '/api/users', '/api/reports')")
    actions: List[str] = Field(
        default=["read", "write", "delete", "modify"],
        description="Available actions for this endpoint (e.g., read, write, delete, modify)"
    )
    description: Optional[str] = Field(None, max_length=500, description="Optional description of the endpoint")


class EndpointResponse(BaseModel):
    endpoint: str
    actions: List[str]
    description: Optional[str]

    class Config:
        from_attributes = True


# User Role Assignment Schema
class UserRoleAssignRequest(BaseModel):
    role_id: UUID = Field(..., description="ID of the role to assign")


# Forgot / Reset Password Schemas
class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    organization_id: UUID


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class ResetPasswordVerifyResponse(BaseModel):
    valid: bool
    email: Optional[str] = None
    message: Optional[str] = None


