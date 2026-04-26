"""Initial schema - Create base tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("entra_id_tenant_id", sa.String(255), nullable=True, unique=True),
        sa.Column("entra_id_client_id", sa.String(255), nullable=True),
        sa.Column("entra_id_client_secret", sa.LargeBinary(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_entra_id_tenant_id", "organizations", ["entra_id_tenant_id"])

    # Create roles table
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roles_organization_id", "roles", ["organization_id"])

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("entra_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_entra_id", "users", ["entra_id"])
    op.create_index("ix_users_username", "users", ["username"])

    # Create user_roles association table
    op.create_table(
        "user_roles",
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    # Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    # Create registered_apps table
    op.create_table(
        "registered_apps",
        sa.Column("id", UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("app_name", sa.String(255), nullable=False),
        sa.Column("app_type", sa.String(50), nullable=False),
        sa.Column("api_key", sa.String(255), nullable=False, unique=True),
        sa.Column("redirect_uris", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_registered_apps_organization_id", "registered_apps", ["organization_id"])
    op.create_index("ix_registered_apps_api_key", "registered_apps", ["api_key"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_registered_apps_api_key", table_name="registered_apps")
    op.drop_index("ix_registered_apps_organization_id", table_name="registered_apps")
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_entra_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_index("ix_roles_organization_id", table_name="roles")
    op.drop_index("ix_organizations_entra_id_tenant_id", table_name="organizations")

    # Drop tables in reverse order
    op.drop_table("registered_apps")
    op.drop_table("user_roles")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("organizations")
