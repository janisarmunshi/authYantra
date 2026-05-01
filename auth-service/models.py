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
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    entra_id_tenant_id = Column(String(255), nullable=True, unique=True)
    entra_id_client_id = Column(String(255), nullable=True)
    entra_id_client_secret = Column(LargeBinary, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="organization", foreign_keys="User.organization_id")
    roles = relationship("Role", back_populates="organization", cascade="all, delete-orphan")
    apps = relationship("RegisteredApp", back_populates="organization", cascade="all, delete-orphan")
    memberships = relationship("UserOrganization", back_populates="organization", cascade="all, delete-orphan")
    invites = relationship("OrgInvite", back_populates="organization", cascade="all, delete-orphan",
                           foreign_keys="OrgInvite.org_id")

    __table_args__ = (
        Index("ix_organizations_entra_id_tenant_id", "entra_id_tenant_id"),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # nullable — new users start without an org; populated when they join/create one (used as active-org context in JWT)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    entra_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="users", foreign_keys=[organization_id])
    roles = relationship("Role", secondary=user_roles_table, back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    memberships = relationship("UserOrganization", back_populates="user",
                               cascade="all, delete-orphan", foreign_keys="UserOrganization.user_id")

    __table_args__ = (
        Index("ix_users_organization_id", "organization_id"),
        Index("ix_users_email", "email"),
        Index("ix_users_entra_id", "entra_id"),
        Index("ix_users_username", "username"),
    )


class UserOrganization(Base):
    """Membership join table — user belongs to org with a role and optional default flag."""
    __tablename__ = "user_organizations"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(50), nullable=False, default="member")  # admin | member
    is_default = Column(Boolean, nullable=False, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="memberships", foreign_keys=[user_id])
    organization = relationship("Organization", back_populates="memberships", foreign_keys=[org_id])

    __table_args__ = (
        Index("ix_user_organizations_user_id", "user_id"),
        Index("ix_user_organizations_org_id", "org_id"),
    )


class OrgInvite(Base):
    """Pending invitation to join an organization."""
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


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    permissions = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="roles")
    users = relationship("User", secondary=user_roles_table, back_populates="roles")

    __table_args__ = (Index("ix_roles_organization_id", "organization_id"),)


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


class RegisteredApp(Base):
    __tablename__ = "registered_apps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    app_name = Column(String(255), nullable=False)
    app_type = Column(String(50), nullable=False)
    api_key = Column(String(255), nullable=False, unique=True)
    redirect_uris = Column(JSON, default=list, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="apps")

    __table_args__ = (
        Index("ix_registered_apps_organization_id", "organization_id"),
        Index("ix_registered_apps_api_key", "api_key"),
    )


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
