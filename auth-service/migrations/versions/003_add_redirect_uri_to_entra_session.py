"""Add redirect_uri to EntraIDSession for multi-app support

Revision ID: 003_add_redirect_uri_to_entra_session
Revises: 002_add_entra_id_session
Create Date: 2026-03-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "003_entra_redirect_uri"
down_revision = "002_entra_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add redirect_uri column to entra_id_sessions table
    op.add_column(
        "entra_id_sessions",
        sa.Column("redirect_uri", sa.String(500), nullable=False, server_default=""),
    )


def downgrade() -> None:
    # Remove redirect_uri column
    op.drop_column("entra_id_sessions", "redirect_uri")
