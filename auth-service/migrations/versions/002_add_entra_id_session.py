"""Add EntraIDSession table for OAuth 2.0 state tracking

Revision ID: 002_add_entra_id_session
Revises:
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = "002_entra_sessions"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create entra_id_sessions table
    op.create_table(
        "entra_id_sessions",
        sa.Column("id", UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(255), nullable=False, unique=True),
        sa.Column("code_verifier", sa.String(255), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_entra_id_sessions_organization_id", "entra_id_sessions", ["organization_id"])
    op.create_index("ix_entra_id_sessions_state", "entra_id_sessions", ["state"])
    op.create_index("ix_entra_id_sessions_expires_at", "entra_id_sessions", ["expires_at"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_entra_id_sessions_expires_at", table_name="entra_id_sessions")
    op.drop_index("ix_entra_id_sessions_state", table_name="entra_id_sessions")
    op.drop_index("ix_entra_id_sessions_organization_id", table_name="entra_id_sessions")

    # Drop table
    op.drop_table("entra_id_sessions")
