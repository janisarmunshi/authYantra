"""Add user_organizations and org_invites; make User.organization_id nullable

Revision ID: 007_org_membership_and_invites
Revises: 006_password_reset_tokens
Create Date: 2026-05-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "007_org_membership_and_invites"
down_revision = "006_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create user_organizations
    op.create_table(
        "user_organizations",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("joined_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_organizations_user_id", "user_organizations", ["user_id"])
    op.create_index("ix_user_organizations_org_id", "user_organizations", ["org_id"])

    # 2. Create org_invites
    op.create_table(
        "org_invites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invited_email", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("invited_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_org_invites_org_id", "org_invites", ["org_id"])
    op.create_index("ix_org_invites_token_hash", "org_invites", ["token_hash"])
    op.create_index("ix_org_invites_invited_email", "org_invites", ["invited_email"])

    # 3. Migrate existing memberships into user_organizations before making nullable
    op.execute("""
        INSERT INTO user_organizations (user_id, org_id, role, is_default, joined_at)
        SELECT id, organization_id, 'admin', true, created_at
        FROM users
        WHERE organization_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """)

    # 4. Drop the old CASCADE FK and add a new SET NULL FK on users.organization_id
    op.drop_constraint("users_organization_id_fkey", "users", type_="foreignkey")
    op.alter_column("users", "organization_id", nullable=True)
    op.create_foreign_key(
        "users_organization_id_fkey",
        "users", "organizations",
        ["organization_id"], ["id"],
        ondelete="SET NULL",
    )

    # 5. Make password_reset_tokens.organization_id nullable (no longer required)
    op.alter_column("password_reset_tokens", "organization_id", nullable=True)

    # 6. Make users.email unique (emails are now global, not per-org)
    # Only add if not already unique
    op.create_index("ix_users_email_unique", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email_unique", "users")
    op.alter_column("password_reset_tokens", "organization_id", nullable=False)
    op.drop_constraint("users_organization_id_fkey", "users", type_="foreignkey")
    op.alter_column("users", "organization_id", nullable=False)
    op.create_foreign_key(
        "users_organization_id_fkey",
        "users", "organizations",
        ["organization_id"], ["id"],
        ondelete="CASCADE",
    )
    op.drop_index("ix_org_invites_invited_email", "org_invites")
    op.drop_index("ix_org_invites_token_hash", "org_invites")
    op.drop_index("ix_org_invites_org_id", "org_invites")
    op.drop_table("org_invites")
    op.drop_index("ix_user_organizations_org_id", "user_organizations")
    op.drop_index("ix_user_organizations_user_id", "user_organizations")
    op.drop_table("user_organizations")
