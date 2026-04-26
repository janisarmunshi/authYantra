"""Create default super user

Revision ID: 004_super_user
Revises: 003_entra_redirect_uri
Create Date: 2026-03-08 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision = '004_super_user'
down_revision = '003_entra_redirect_uri'
branch_labels = None
depends_on = None

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    """Create super user organization, role, and user"""
    
    # Create super user organization
    super_org_id = uuid.uuid4()
    op.execute(
        f"""
        INSERT INTO organizations (id, name, is_active, created_at, updated_at)
        VALUES ('{super_org_id}', 'System Admin', true, NOW(), NOW())
        """
    )
    
    # Create super_user role
    super_role_id = uuid.uuid4()
    op.execute(
        f"""
        INSERT INTO roles (id, organization_id, name, permissions, is_active, created_at, updated_at)
        VALUES ('{super_role_id}', '{super_org_id}', 'super_user', '{{"*": ["read", "write", "delete", "modify"]}}'::jsonb, true, NOW(), NOW())
        """
    )
    
    # Create super user
    # Default password: admin123 (you MUST change this after first login)
    super_user_id = uuid.uuid4()
    password_hash = pwd_context.hash("admin123")
    
    op.execute(
        f"""
        INSERT INTO users (id, organization_id, email, username, password_hash, is_active, created_at, updated_at)
        VALUES ('{super_user_id}', '{super_org_id}', 'admin@authyantra.com', 'superadmin', '{password_hash}', true, NOW(), NOW())
        """
    )
    
    # Assign super_user role to the super user
    op.execute(
        f"""
        INSERT INTO user_roles (user_id, role_id)
        VALUES ('{super_user_id}', '{super_role_id}')
        """
    )


def downgrade() -> None:
    """Remove super user, role, and organization"""
    
    # Get the super user organization
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id FROM organizations WHERE name = 'System Admin' LIMIT 1")
    )
    row = result.fetchone()
    
    if row:
        # Delete will cascade to users, roles, and other dependent tables
        conn.execute(
            sa.text("DELETE FROM organizations WHERE id = :id"),
            {"id": row[0]}
        )
