import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Table,
    JSON,
    Index,
    LargeBinary,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Association table for user-role relationship
user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Organization(Base):
    """Organization model for multi-tenancy"""

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    entra_id_tenant_id = Column(String(255), nullable=True, unique=True)
    entra_id_client_id = Column(String(255), nullable=True)
    entra_id_client_secret = Column(LargeBinary, nullable=True)  # Encrypted
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="organization", cascade="all, delete-orphan")
    apps = relationship("RegisteredApp", back_populates="organization", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_organizations_entra_id_tenant_id", "entra_id_tenant_id"),
    )


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)  # For local auth
    entra_id = Column(String(255), nullable=True)  # For SSO users
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    roles = relationship("Role", secondary=user_roles_table, back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_organization_id", "organization_id"),
        Index("ix_users_email", "email"),
        Index("ix_users_entra_id", "entra_id"),
        Index("ix_users_username", "username"),
    )


class Role(Base):
    """Role model for role-based authorization"""

    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    permissions = Column(JSON, default=dict, nullable=False)  # Dict: endpoint -> list of actions
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="roles")
    users = relationship("User", secondary=user_roles_table, back_populates="roles")

    __table_args__ = (
        Index("ix_roles_organization_id", "organization_id"),
    )


class RefreshToken(Base):
    """Refresh token model for tracking and revocation"""

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True)  # Hash of the token
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )


class RegisteredApp(Base):
    """Registered application for rate limiting and OAuth redirect URIs"""

    __tablename__ = "registered_apps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    app_name = Column(String(255), nullable=False)
    app_type = Column(String(50), nullable=False)  # web, desktop, mobile
    api_key = Column(String(255), nullable=False, unique=True)  # For rate limiting
    redirect_uris = Column(JSON, default=list, nullable=False)  # List of allowed redirect URIs
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="apps")

    __table_args__ = (
        Index("ix_registered_apps_organization_id", "organization_id"),
        Index("ix_registered_apps_api_key", "api_key"),
    )


class RegisteredEndpoint(Base):
    """API endpoints registered by an organization for RBAC"""

    __tablename__ = "registered_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(String(255), nullable=False)
    actions = Column(JSON, default=list, nullable=False)  # List of allowed action strings
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_registered_endpoints_org_id", "organization_id"),
    )


class PasswordResetToken(Base):
    """Password reset token for forgot-password flow"""

    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True)  # SHA-256 hash of the raw token
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_password_reset_tokens_user_id", "user_id"),
        Index("ix_password_reset_tokens_token_hash", "token_hash"),
        Index("ix_password_reset_tokens_expires_at", "expires_at"),
    )


class EntraIDSession(Base):
    """OAuth 2.0 session state tracking for Entra ID authentication"""

    __tablename__ = "entra_id_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    state = Column(String(255), nullable=False, unique=True)  # CSRF protection token
    code_verifier = Column(String(255), nullable=False)  # PKCE code verifier
    user_id = Column(UUID(as_uuid=True), nullable=True)  # For account linking mode
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_entra_id_sessions_organization_id", "organization_id"),
        Index("ix_entra_id_sessions_state", "state"),
        Index("ix_entra_id_sessions_expires_at", "expires_at"),
    )
