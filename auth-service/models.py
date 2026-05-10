import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey,
    Table, JSON, Index, LargeBinary, Text, Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# ---------------------------------------------------------------------------
# Association table: user ↔ role
# ---------------------------------------------------------------------------
user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

# Membership privilege ordering (higher = more privileged)
ROLE_HIERARCHY = {
    "owner": 6, "admin": 5, "developer": 4,
    "auditor": 3, "billing": 2, "member": 1,
}


# ---------------------------------------------------------------------------
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=True, unique=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    entra_id_tenant_id = Column(String(255), nullable=True, unique=True)
    entra_id_client_id = Column(String(255), nullable=True)
    entra_id_client_secret = Column(LargeBinary, nullable=True)
    is_active = Column(Boolean, default=True)
    mfa_required = Column(Boolean, default=False)
    allowed_email_domains = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="organization", foreign_keys="User.organization_id")
    roles = relationship("Role", back_populates="organization", cascade="all, delete-orphan", passive_deletes=True)
    apps = relationship("RegisteredApp", back_populates="organization", cascade="all, delete-orphan", passive_deletes=True)
    memberships = relationship("UserOrganization", back_populates="organization", cascade="all, delete-orphan", passive_deletes=True)
    invites = relationship("OrgInvite", back_populates="organization", cascade="all, delete-orphan", foreign_keys="OrgInvite.org_id", passive_deletes=True)
    identity_providers = relationship("IdentityProvider", back_populates="organization", cascade="all, delete-orphan", passive_deletes=True)
    audit_logs = relationship("AuditLog", back_populates="organization", passive_deletes=True)

    __table_args__ = (
        Index("ix_organizations_entra_id_tenant_id", "entra_id_tenant_id"),
        Index("ix_organizations_slug", "slug"),
    )


# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    email = Column(String(255), nullable=False, unique=True)
    email_verified = Column(Boolean, default=False)
    username = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    password_hash = Column(String(255), nullable=True)
    entra_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="users", foreign_keys=[organization_id])
    roles = relationship("Role", secondary=user_roles_table, back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    memberships = relationship("UserOrganization", back_populates="user", cascade="all, delete-orphan", passive_deletes=True, foreign_keys="UserOrganization.user_id")
    mfa_credentials = relationship("MfaCredential", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    audit_logs = relationship("AuditLog", back_populates="user", passive_deletes=True)

    __table_args__ = (
        Index("ix_users_organization_id", "organization_id"),
        Index("ix_users_email", "email"),
        Index("ix_users_entra_id", "entra_id"),
        Index("ix_users_username", "username"),
    )


# ---------------------------------------------------------------------------
class UserOrganization(Base):
    """Membership — role: owner | admin | developer | auditor | billing | member"""
    __tablename__ = "user_organizations"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(50), nullable=False, default="member")
    is_default = Column(Boolean, nullable=False, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="memberships", foreign_keys=[user_id])
    organization = relationship("Organization", back_populates="memberships", foreign_keys=[org_id])

    __table_args__ = (
        Index("ix_user_organizations_user_id", "user_id"),
        Index("ix_user_organizations_org_id", "org_id"),
    )


# ---------------------------------------------------------------------------
class OrgInvite(Base):
    __tablename__ = "org_invites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    invited_email = Column(String(255), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True)
    role = Column(String(50), nullable=False, default="member")
    invited_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="invites", foreign_keys=[org_id])

    __table_args__ = (
        Index("ix_org_invites_org_id", "org_id"),
        Index("ix_org_invites_token_hash", "token_hash"),
        Index("ix_org_invites_invited_email", "invited_email"),
    )


# ---------------------------------------------------------------------------
class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    permissions = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="roles")
    users = relationship("User", secondary=user_roles_table, back_populates="roles")

    __table_args__ = (Index("ix_roles_organization_id", "organization_id"),)


# ---------------------------------------------------------------------------
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )


# ---------------------------------------------------------------------------
class RegisteredApp(Base):
    __tablename__ = "registered_apps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    app_name = Column(String(255), nullable=False)
    app_type = Column(String(50), nullable=False)           # web | desktop | mobile | service
    client_id = Column(String(255), nullable=True, unique=True)    # OAuth 2.0 client_id
    client_secret_hash = Column(String(255), nullable=True)        # None = public client
    api_key = Column(String(255), nullable=False, unique=True)
    redirect_uris = Column(JSON, default=list, nullable=False)
    allowed_scopes = Column(JSON, default=list, nullable=False)
    allowed_grant_types = Column(JSON, default=list, nullable=False)
    access_token_lifetime = Column(Integer, default=900)
    refresh_token_lifetime = Column(Integer, default=604800)
    is_active = Column(Boolean, default=True)
    is_confidential = Column(Boolean, default=True)
    logo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="apps")
    oauth_codes = relationship("OAuth2AuthCode", back_populates="app", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        Index("ix_registered_apps_organization_id", "organization_id"),
        Index("ix_registered_apps_api_key", "api_key"),
        Index("ix_registered_apps_client_id", "client_id"),
    )


# ---------------------------------------------------------------------------
class RegisteredEndpoint(Base):
    __tablename__ = "registered_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(String(255), nullable=False)
    actions = Column(JSON, default=list, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_registered_endpoints_org_id", "organization_id"),)


# ---------------------------------------------------------------------------
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_password_reset_tokens_user_id", "user_id"),
        Index("ix_password_reset_tokens_token_hash", "token_hash"),
        Index("ix_password_reset_tokens_expires_at", "expires_at"),
    )


# ---------------------------------------------------------------------------
class EntraIDSession(Base):
    __tablename__ = "entra_id_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    state = Column(String(255), nullable=False, unique=True)
    code_verifier = Column(String(255), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_entra_id_sessions_organization_id", "organization_id"),
        Index("ix_entra_id_sessions_state", "state"),
        Index("ix_entra_id_sessions_expires_at", "expires_at"),
    )


# ===========================================================================
# NEW TABLES
# ===========================================================================

class MfaCredential(Base):
    """TOTP / email-OTP credentials per user"""
    __tablename__ = "mfa_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)                    # totp | email
    secret_encrypted = Column(Text, nullable=True)               # Fernet-encrypted TOTP secret
    backup_codes_encrypted = Column(Text, nullable=True)         # Fernet-encrypted JSON list
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="mfa_credentials")

    __table_args__ = (Index("ix_mfa_credentials_user_id", "user_id"),)


class Session(Base):
    """Long-lived SSO session record"""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    session_token_hash = Column(String(255), nullable=False, unique=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    last_active_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_session_token_hash", "session_token_hash"),
        Index("ix_sessions_expires_at", "expires_at"),
    )


class IdentityProvider(Base):
    """Per-org IdP: google | github | microsoft | saml | oidc | magic_link"""
    __tablename__ = "identity_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    config_encrypted = Column(Text, nullable=True)        # Fernet-encrypted JSON config
    attribute_mapping = Column(JSON, default=dict, nullable=False)
    auto_provision = Column(Boolean, default=True)
    default_role = Column(String(50), default="member")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="identity_providers")

    __table_args__ = (Index("ix_identity_providers_organization_id", "organization_id"),)


class OAuth2AuthCode(Base):
    """Short-lived authorization codes for OAuth 2.0 Authorization Code flow"""
    __tablename__ = "oauth2_auth_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(UUID(as_uuid=True), ForeignKey("registered_apps.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    code_hash = Column(String(255), nullable=False, unique=True)
    redirect_uri = Column(String(500), nullable=False)
    scopes = Column(JSON, default=list, nullable=False)
    code_challenge = Column(String(255), nullable=True)        # PKCE
    code_challenge_method = Column(String(10), nullable=True)  # S256 | plain
    nonce = Column(String(255), nullable=True)                 # OIDC nonce
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    app = relationship("RegisteredApp", back_populates="oauth_codes")

    __table_args__ = (
        Index("ix_oauth2_auth_codes_code_hash", "code_hash"),
        Index("ix_oauth2_auth_codes_app_id", "app_id"),
        Index("ix_oauth2_auth_codes_expires_at", "expires_at"),
    )


class AuditLog(Base):
    """Immutable audit trail — never updated, never cascade-deleted"""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)       # "user.login", "org.member_added", …
    resource_type = Column(String(50), nullable=True)  # user | org | app | role | mfa | idp
    resource_id = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="success")  # success | failure
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_org_id", "org_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
