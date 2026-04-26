"""
Comprehensive Regression Test Suite for Auth Service

Tests all endpoints and workflows to ensure complete functionality after changes.
"""

import pytest
import asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import sys
import os
from config import get_settings
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from models import Base, Organization, User, Role
from database import get_db_session
import json
from sqlalchemy import select, and_

settings = get_settings()

# Test counter for rate limiting
test_counter = 0


# Test database setup - use PostgreSQL from settings
@pytest.fixture
async def test_db():
    """Create test database session using PostgreSQL"""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(test_db):
    """Create test client with test database"""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db_session] = override_get_db
    client = AsyncClient(app=app, base_url="http://test")
    # Add small delay to avoid rate limiting
    await asyncio.sleep(0.1)
    return client


def rate_limit_aware_delay():
    """Add delay between operations that hit rate limits"""
    global test_counter
    test_counter += 1
    if test_counter % 5 == 0:
        time.sleep(1.5)  # Wait 1.5 seconds every 5 operations to avoid rate limit


# ============================================================================
# HEALTH & ROOT ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint returns app info"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "docs" in data


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


# ============================================================================
# ORGANIZATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_organization(client, test_db):
    """Test organization creation with auto-created roles"""
    org_data = {
        "name": "Test Organization",
        "entra_id_tenant_id": str(uuid4()),
    }
    
    response = await client.post("/orgs", json=org_data)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data["name"] == "Test Organization"
    assert "id" in data
    
    org_id = data["id"]
    
    # Verify default roles were created
    from sqlalchemy import select
    result = await test_db.execute(
        select(Role).where(Role.organization_id == org_id)
    )
    roles = result.scalars().all()
    role_names = [r.name for r in roles]
    
    assert "admin" in role_names, f"Admin role not found in {role_names}"
    assert "user" in role_names, f"User role not found in {role_names}"
    return org_id


# ============================================================================
# USER REGISTRATION & AUTHENTICATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_user_registration(client, test_db):
    """Test user registration"""
    # First create an organization
    org_response = await client.post(
        "/orgs",
        json={"name": "Test Org", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_response.json()["id"]
    
    # Register a user
    user_data = {
        "organization_id": org_id,
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
    }
    
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "user_id" in data
    assert data["message"] == "User registered successfully"
    
    user_id = data["user_id"]
    return org_id, user_id


@pytest.mark.asyncio
async def test_user_login(client, test_db):
    """Test user login and token generation"""
    # Create org and user
    org_response = await client.post(
        "/orgs",
        json={"name": "Test Org", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_response.json()["id"]
    
    user_data = {
        "organization_id": org_id,
        "email": "logintest@example.com",
        "username": "logintest",
        "password": "LoginTest123!",
    }
    
    await client.post("/auth/register", json=user_data)
    
    # Login
    login_data = {
        "email": "logintest@example.com",
        "password": "LoginTest123!",
    }
    
    response = await client.post(
        "/auth/login",
        json=login_data,
        headers={"organization-id": org_id}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    
    access_token = data["access_token"]
    
    return org_id, access_token


@pytest.mark.asyncio
async def test_get_current_user(client, test_db):
    """Test getting current user info"""
    # Create org and user, get token
    org_response = await client.post(
        "/orgs",
        json={"name": "Test Org", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_response.json()["id"]
    
    user_data = {
        "organization_id": org_id,
        "email": "metest@example.com",
        "username": "metest",
        "password": "MeTest123!",
    }
    
    await client.post("/auth/register", json=user_data)
    
    login_response = await client.post(
        "/auth/login",
        json={"email": "metest@example.com", "password": "MeTest123!"},
        headers={"organization_id": org_id}
    )
    
    access_token = login_response.json()["access_token"]
    
    # Get current user
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data["email"] == "metest@example.com"


@pytest.mark.asyncio
async def test_change_password(client, test_db):
    """Test password change endpoint"""
    # Create org and user
    org_response = await client.post(
        "/orgs",
        json={"name": "Test Org", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_response.json()["id"]
    
    user_data = {
        "organization_id": org_id,
        "email": "pwdtest@example.com",
        "username": "pwdtest",
        "password": "OldPassword123!",
    }
    
    await client.post("/auth/register", json=user_data)
    
    login_response = await client.post(
        "/auth/login",
        json={"email": "pwdtest@example.com", "password": "OldPassword123!"},
        headers={"organization_id": org_id}
    )
    
    access_token = login_response.json()["access_token"]
    
    # Change password
    response = await client.post(
        "/auth/change-password",
        json={"old_password": "OldPassword123!", "new_password": "NewPassword123!"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "Password changed successfully" in data["message"]
    
    # Verify old password doesn't work and new one does
    bad_login = await client.post(
        "/auth/login",
        json={"email": "pwdtest@example.com", "password": "OldPassword123!"},
        headers={"organization-id": org_id}
    )
    assert bad_login.status_code == 401
    
    good_login = await client.post(
        "/auth/login",
        json={"email": "pwdtest@example.com", "password": "NewPassword123!"},
        headers={"organization-id": org_id}
    )
    assert good_login.status_code == 200


@pytest.mark.asyncio
async def test_token_refresh(client, test_db):
    """Test token refresh endpoint"""
    # Create org and user, get tokens
    org_response = await client.post(
        "/orgs",
        json={"name": "Test Org", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_response.json()["id"]
    
    user_data = {
        "organization_id": org_id,
        "email": "refreshtest@example.com",
        "username": "refreshtest",
        "password": "RefreshTest123!",
    }
    
    await client.post("/auth/register", json=user_data)
    
    login_response = await client.post(
        "/auth/login",
        json={"email": "refreshtest@example.com", "password": "RefreshTest123!"},
        headers={"organization_id": org_id}
    )
    
    refresh_token = login_response.json()["refresh_token"]
    old_access_token = login_response.json()["access_token"]
    
    # Refresh token
    response = await client.post(
        "/auth/token/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "access_token" in data
    assert data["access_token"] != old_access_token  # Should be a new token


@pytest.mark.asyncio
async def test_token_verify(client, test_db):
    """Test token verification endpoint"""
    # Get a valid token
    org_response = await client.post(
        "/orgs",
        json={"name": "Test Org", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_response.json()["id"]
    
    user_data = {
        "organization_id": org_id,
        "email": "verifytest@example.com",
        "username": "verifytest",
        "password": "VerifyTest123!",
    }
    
    await client.post("/auth/register", json=user_data)
    
    login_response = await client.post(
        "/auth/login",
        json={"email": "verifytest@example.com", "password": "VerifyTest123!"},
        headers={"organization-id": org_id}
    )
    
    access_token = login_response.json()["access_token"]
    
    # Verify token
    response = await client.post(
        "/auth/token/verify",
        json={"token": access_token}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data["valid"] is True
    
    # Verify invalid token
    response = await client.post(
        "/auth/token/verify",
        json={"token": "invalid.token.here"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False


# ============================================================================
# ROLE & ENDPOINT MANAGEMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_register_endpoint(client, test_db):
    """Test endpoint registration - must be done by admin"""
    # Create org
    org_response = await client.post(
        "/orgs",
        json={"name": "Test Org", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_response.json()["id"]
    
    # Get admin role for this org
    from sqlalchemy import select
    result = await test_db.execute(
        select(Role).where(
            and_(Role.organization_id == org_id, Role.name == "admin")
        )
    )
    admin_role = result.scalar_one_or_none()
    
    # Create admin user
    admin_user_data = {
        "organization_id": org_id,
        "email": "endpointadmin@example.com",
        "username": "endpointadmin",
        "password": "EndpointAdmin123!",
    }
    
    await client.post("/auth/register", json=admin_user_data)
    
    # Get admin user from database and assign admin role
    admin_user_result = await test_db.execute(
        select(User).where(User.email == "endpointadmin@example.com")
    )
    admin_user = admin_user_result.scalar_one_or_none()
    if admin_user and admin_role and admin_role not in admin_user.roles:
        admin_user.roles.append(admin_role)
        await test_db.commit()
    
    # Login as admin
    login_response = await client.post(
        "/auth/login",
        json={"email": "endpointadmin@example.com", "password": "EndpointAdmin123!"},
        headers={"organization-id": org_id}
    )
    
    assert "access_token" in login_response.json(), f"Failed to login: {login_response.json()}"
    access_token = login_response.json()["access_token"]
    
    # Register endpoint
    endpoint_data = {
        "endpoint": "/api/users",
        "actions": ["read", "write", "delete"],
        "description": "User management endpoint"
    }
    
    response = await client.post(
        f"/endpoints/{org_id}/register",
        json=endpoint_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data["endpoint"] == "/api/users"


@pytest.mark.asyncio
async def test_list_endpoints(client, test_db):
    """Test listing registered endpoints"""
    # Create org and authenticated user
    org_response = await client.post(
        "/orgs",
        json={"name": "Test Org", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_response.json()["id"]
    
    user_data = {
        "organization_id": org_id,
        "email": "listendpointtest@example.com",
        "username": "listendpointtest",
        "password": "ListEndpointTest123!",
    }
    
    await client.post("/auth/register", json=user_data)
    
    login_response = await client.post(
        "/auth/login",
        json={"email": "listendpointtest@example.com", "password": "ListEndpointTest123!"},
        headers={"organization-id": org_id}
    )
    
    access_token = login_response.json()["access_token"]
    
    # Register some endpoints
    await client.post(
        f"/endpoints/{org_id}/register",
        json={"endpoint": "/api/users", "actions": ["read", "write"]},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    await client.post(
        f"/endpoints/{org_id}/register",
        json={"endpoint": "/api/reports", "actions": ["read"]},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # List endpoints
    response = await client.get(
        f"/endpoints/{org_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    endpoints = [ep["endpoint"] for ep in data]
    assert "/api/users" in endpoints
    assert "/api/reports" in endpoints


@pytest.mark.asyncio
async def test_create_role(client, test_db):
    """Test role creation with endpoint permissions - must be done by admin"""
    # Create org
    org_response = await client.post(
        "/orgs",
        json={"name": "Test Org", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_response.json()["id"]
    
    # Get admin role for this org
    result = await test_db.execute(
        select(Role).where(
            and_(Role.organization_id == org_id, Role.name == "admin")
        )
    )
    admin_role = result.scalar_one_or_none()
    
    # Create admin user
    admin_user_data = {
        "organization_id": org_id,
        "email": "roleadmin@example.com",
        "username": "roleadmin",
        "password": "RoleAdmin123!",
    }
    
    await client.post("/auth/register", json=admin_user_data)
    
    # Get admin user from database and assign admin role
    admin_user_result = await test_db.execute(
        select(User).where(User.email == "roleadmin@example.com")
    )
    admin_user = admin_user_result.scalar_one_or_none()
    if admin_user and admin_role and admin_role not in admin_user.roles:
        admin_user.roles.append(admin_role)
        await test_db.commit()
    
    # Login as admin
    login_response = await client.post(
        "/auth/login",
        json={"email": "roleadmin@example.com", "password": "RoleAdmin123!"},
        headers={"organization-id": org_id}
    )
    
    assert "access_token" in login_response.json(), f"Failed to login: {login_response.json()}"
    access_token = login_response.json()["access_token"]
    
    # Create role with permissions
    role_data = {
        "name": "viewer",
        "permissions": {
            "/api/users": ["read"],
            "/api/reports": ["read"]
        },
        "is_active": True
    }
    
    response = await client.post(
        f"/roles/{org_id}",
        json=role_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data["name"] == "viewer"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_roles(client, test_db):
    """Test listing organizational roles"""
    # Create org and authenticated user
    org_response = await client.post(
        "/orgs",
        json={"name": "Test Org", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_response.json()["id"]
    
    user_data = {
        "organization_id": org_id,
        "email": "listroletest@example.com",
        "username": "listroletest",
        "password": "ListRoleTest123!",
    }
    
    await client.post("/auth/register", json=user_data)
    
    login_response = await client.post(
        "/auth/login",
        json={"email": "listroletest@example.com", "password": "ListRoleTest123!"},
        headers={"organization-id": org_id}
    )
    
    access_token = login_response.json()["access_token"]
    
    # List roles (should have default admin and user roles)
    response = await client.get(
        f"/roles/{org_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # At least admin and user roles
    role_names = [role["name"] for role in data]
    assert "admin" in role_names
    assert "user" in role_names


# ============================================================================
# ACCESS CONTROL TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_access_control_own_org_only(client, test_db):
    """Test that users can only access their own organization"""
    # Create first org and user
    org1_response = await client.post(
        "/orgs",
        json={"name": "Org 1", "entra_id_tenant_id": str(uuid4())}
    )
    org1_id = org1_response.json()["id"]
    
    user1_data = {
        "organization_id": org1_id,
        "email": "user1@example.com",
        "username": "user1",
        "password": "User1Test123!",
    }
    
    await client.post("/auth/register", json=user1_data)
    
    login1_response = await client.post(
        "/auth/login",
        json={"email": "user1@example.com", "password": "User1Test123!"},
        headers={"organization-id": org1_id}
    )
    
    user1_token = login1_response.json()["access_token"]
    
    # Create second org
    org2_response = await client.post(
        "/orgs",
        json={"name": "Org 2", "entra_id_tenant_id": str(uuid4())}
    )
    org2_id = org2_response.json()["id"]
    
    # User1 should NOT be able to access org2
    response = await client.get(
        f"/orgs/{org2_id}",
        headers={"Authorization": f"Bearer {user1_token}"}
    )
    assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


# ============================================================================
# COMPREHENSIVE WORKFLOW TEST
# ============================================================================

@pytest.mark.asyncio
async def test_complete_workflow(client, test_db):
    """Test a complete workflow from organization to role assignment"""
    
    # 1. Create organization
    org_response = await client.post(
        "/orgs",
        json={"name": "Workflow Test Org", "entra_id_tenant_id": str(uuid4())}
    )
    assert org_response.status_code == 200
    org_id = org_response.json()["id"]
    
    # 2. Register user
    user_data = {
        "organization_id": org_id,
        "email": "workflow@example.com",
        "username": "workflow",
        "password": "WorkflowTest123!",
    }
    
    user_response = await client.post("/auth/register", json=user_data)
    assert user_response.status_code == 200
    
    # 3. Login
    login_response = await client.post(
        "/auth/login",
        json={"email": "workflow@example.com", "password": "WorkflowTest123!"},
        headers={"organization-id": org_id}
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    
    # 4. Register endpoints
    await client.post(
        f"/endpoints/{org_id}/register",
        json={"endpoint": "/api/users", "actions": ["read", "write", "delete"]},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # 5. Create custom role
    role_response = await client.post(
        f"/roles/{org_id}",
        json={
            "name": "custom_viewer",
            "permissions": {"/api/users": ["read"]},
            "is_active": True
        },
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert role_response.status_code == 200
    custom_role_id = role_response.json()["id"]
    
    # 6. List roles
    list_response = await client.get(
        f"/roles/{org_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert list_response.status_code == 200
    roles = list_response.json()
    assert len(roles) >= 3  # admin, user, custom_viewer
    
    # 7. Register another user
    user2_data = {
        "organization_id": org_id,
        "email": "workflow2@example.com",
        "username": "workflow2",
        "password": "Workflow2Test123!",
    }
    await client.post("/auth/register", json=user2_data)
    
    # Get second user ID
    login2_response = await client.post(
        "/auth/login",
        json={"email": "workflow2@example.com", "password": "Workflow2Test123!"},
        headers={"organization-id": org_id}
    )
    user2_info = login2_response.json()  # Contains the user info
    
    # Extract user_id from the auth service or from the database
    # For now, we'll use the email-based lookup
    from services.user_service import UserService
    from sqlalchemy import select
    result = await test_db.execute(
        select(User).where(User.email == "workflow2@example.com")
    )
    user2_obj = result.scalar_one_or_none()
    user2_id = str(user2_obj.id) if user2_obj else None
    
    if user2_id:
        # 8. Assign role to user
        assign_response = await client.post(
            f"/users/{user2_id}/roles/{org_id}",
            json={"role_id": custom_role_id},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert assign_response.status_code == 200
        
        # 9. List user roles
        user_roles_response = await client.get(
            f"/users/{user2_id}/roles/{org_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert user_roles_response.status_code == 200
        user_roles = user_roles_response.json()
        assert len(user_roles) > 0


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
