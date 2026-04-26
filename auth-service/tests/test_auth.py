import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from models import Base, Organization, User
from services.user_service import UserService
from services.token_service import TokenService
from database import get_db_session


# Test database setup
@pytest.fixture
async def test_db():
    """Create test database session"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def test_org(test_db):
    """Create test organization"""
    org = Organization(id=uuid4(), name="Test Org")
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)
    return org


@pytest.fixture
def client(test_db):
    """Create test client"""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db_session] = override_get_db
    return TestClient(app)


# Tests
@pytest.mark.asyncio
async def test_user_registration(test_db, test_org):
    """Test user registration"""
    user, error = await UserService.register_user(
        db=test_db,
        organization_id=test_org.id,
        email="test@example.com",
        password="securepassword123",
        username="testuser",
    )

    assert error is None
    assert user is not None
    assert user.email == "test@example.com"
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_password_hashing():
    """Test password hashing"""
    password = "mysecurepassword"
    hashed = UserService.hash_password(password)

    assert hashed != password
    assert UserService.verify_password(password, hashed)
    assert not UserService.verify_password("wrongpassword", hashed)


@pytest.mark.asyncio
async def test_token_creation():
    """Test JWT token creation and validation"""
    user_id = uuid4()
    org_id = uuid4()
    roles = ["user"]

    access_token = TokenService.create_access_token(user_id, org_id, roles)
    refresh_token = TokenService.create_refresh_token(user_id, org_id)

    assert access_token is not None
    assert refresh_token is not None

    # Verify tokens
    access_payload = TokenService.verify_access_token(access_token)
    refresh_payload = TokenService.verify_refresh_token(refresh_token)

    assert access_payload is not None
    assert refresh_payload is not None
    assert str(user_id) == access_payload.get("sub")
    assert str(org_id) == access_payload.get("org_id")


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_duplicate_email_registration(test_db, test_org):
    """Test duplicate email rejection"""
    # Register first user
    user1, error1 = await UserService.register_user(
        db=test_db,
        organization_id=test_org.id,
        email="test@example.com",
        password="password123",
    )
    assert error1 is None

    # Try to register with same email
    user2, error2 = await UserService.register_user(
        db=test_db,
        organization_id=test_org.id,
        email="test@example.com",
        password="password456",
    )
    assert error2 is not None
    assert "already registered" in error2.lower()


@pytest.mark.asyncio
async def test_authentication(test_db, test_org):
    """Test user authentication"""
    # Register user
    await UserService.register_user(
        db=test_db,
        organization_id=test_org.id,
        email="auth@example.com",
        password="testpassword123",
    )

    # Authenticate
    user, error = await UserService.authenticate_user(
        db=test_db,
        organization_id=test_org.id,
        email="auth@example.com",
        password="testpassword123",
    )

    assert error is None
    assert user is not None
    assert user.email == "auth@example.com"

    # Try wrong password
    user, error = await UserService.authenticate_user(
        db=test_db,
        organization_id=test_org.id,
        email="auth@example.com",
        password="wrongpassword",
    )

    assert error is not None
    assert user is None
