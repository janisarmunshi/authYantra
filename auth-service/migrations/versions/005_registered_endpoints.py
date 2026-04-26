"""Add registered endpoints table

Revision ID: 005_registered_endpoints
Revises: 004_super_user
Create Date: 2026-03-08 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '005_registered_endpoints'
down_revision = '004_super_user'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create registered_endpoints table"""
    # Drop the table if it exists (in case of partial previous migration run)
    op.execute('DROP TABLE IF EXISTS registered_endpoints CASCADE;')
    
    op.create_table(
        'registered_endpoints',
        sa.Column('id', UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', UUID(as_uuid=True), nullable=False),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('actions', JSONB(), nullable=False, server_default='[]'),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'endpoint', name='ix_unique_org_endpoint')
    )
    op.create_index('ix_registered_endpoints_org_id', 'registered_endpoints', ['organization_id'])


def downgrade() -> None:
    """Drop registered_endpoints table"""
    op.drop_index('ix_registered_endpoints_org_id', table_name='registered_endpoints')
    op.drop_table('registered_endpoints')
