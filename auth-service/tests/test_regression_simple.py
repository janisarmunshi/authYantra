"""
Simplified Regression Test Suite for Auth Service
Tests core endpoints and workflows
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from models import Base
from database import get_db_session

settings = get_settings()


@pytest.fixture
async def test_db():
    """Create test database session using PostgreSQL"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
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
    return AsyncClient(app=app, base_url="http://test")


# ============== ENDPOINT TESTS ==============

@pytest.mark.asyncio
async def test_01_root(client):
    """Test root endpoint"""
    response = await client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()


@pytest.mark.asyncio
async def test_02_health(client):
    """Test health check"""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_03_org_creation(client):
    """Test organization creation"""
    response = await client.post(
        "/orgs",
        json={"name": "TestOrg", "entra_id_tenant_id": str(uuid4())}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "TestOrg"


@pytest.mark.asyncio
async def test_04_user_register(client):
    """Test user registration"""
    # Create org first
    org_resp = await client.post(
        "/orgs",
        json={"name": "TestOrg", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_resp.json()["id"]
    
    # Register user
    response = await client.post(
        "/auth/register",
        json={
            "organization_id": org_id,
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPass123!"
        }
    )
    assert response.status_code == 200
    assert "user_id" in response.json()


@pytest.mark.asyncio
async def test_05_user_login(client):
    """Test user login"""
    # Create org
    org_resp = await client.post(
        "/orgs",
        json={"name": "LoginTestOrg", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_resp.json()["id"]
    
    # Register user
    await client.post(
        "/auth/register",
        json={
            "organization_id": org_id,
            "email": "login@example.com",
            "username": "loginuser",
            "password": "LoginPass123!"
        }
    )
    
    # Login
    response = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "LoginPass123!"},
        headers={"organization-id": org_id}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


@pytest.mark.asyncio
async def test_06_token_verify(client):
    """Test token verification"""
    # Get a token first
    org_resp = await client.post(
        "/orgs",
        json={"name": "TokenTestOrg", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_resp.json()["id"]
    
    await client.post(
        "/auth/register",
        json={
            "organization_id": org_id,
            "email": "token@example.com",
            "username": "tokenuser",
            "password": "TokenPass123!"
        }
    )
    
    login_resp = await client.post(
        "/auth/login",
        json={"email": "token@example.com", "password": "TokenPass123!"},
        headers={"organization-id": org_id}
    )
    token = login_resp.json()["access_token"]
    
    # Verify token
    response = await client.post(
        "/auth/token/verify",
        json={"token": token}
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True
    
    # Verify invalid token
    response = await client.post(
        "/auth/token/verify",
        json={"token": "invalid.token"}
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False


@pytest.mark.asyncio
async def test_07_list_roles(client):
    """Test listing organization roles"""
    # Create org (auto-creates admin and user roles)
    org_resp = await client.post(
        "/orgs",
        json={"name": "RoleTestOrg", "entra_id_tenant_id": str(uuid4())}
    )
    org_id = org_resp.json()["id"]
    
    # Create and login user
    await client.post(
        "/auth/register",
        json={
            "organization_id": org_id,
            "email": "roleuser@example.com",
            "username": "roleuser",
            "password": "RoleUserPass123!"
        }
    )
    
    login_resp = await client.post(
        "/auth/login",
        json={"email": "roleuser@example.com", "password": "RoleUserPass123!"},
        headers={"organization-id": org_id}
    )
    token = login_resp.json()["access_token"]
    
    # List roles
    response = await client.get(
        f"/roles/{org_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) >= 2
    role_names = [r["name"] for r in roles]
    assert "admin" in role_names
    assert "user" in role_names


@pytest.mark.asyncio
async def test_08_complete_workflow(client):
    """Test complete workflow: create org, register user, login, and access endpoints"""
    # 1. Create organization
    org_resp = await client.post(
        "/orgs",
        json={"name": "CompleteWorkflowOrg", "entra_id_tenant_id": str(uuid4())}
    )
    assert org_resp.status_code == 200
    org_id = org_resp.json()["id"]
    
    # 2. Register user
    user_resp = await client.post(
        "/auth/register",
        json={
            "organization_id": org_id,
            "email": "workflow@example.com",
            "username": "workflowuser",
            "password": "WorkflowPass123!"
        }
    )
    assert user_resp.status_code == 200
    
    # 3. Login
    login_resp = await client.post(
        "/auth/login",
        json={"email": "workflow@example.com", "password": "WorkflowPass123!"},
        headers={"organization-id": org_id}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    
    # 4. Get current user
    me_resp = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "workflow@example.com"
    
    # 5. List org roles
    roles_resp = await client.get(
        f"/roles/{org_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert roles_resp.status_code == 200
    assert len(roles_resp.json()) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
