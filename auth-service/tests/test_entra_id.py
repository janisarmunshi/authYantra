import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import base64
import hashlib
import httpx

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Organization, User, EntraIDSession
from services.entra_id_service import EntraIDService
from config import get_settings

settings = get_settings()


# Test fixtures
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
    """Create test organization with Entra ID config"""
    org = Organization(
        id=uuid4(),
        name="Test Organization",
        entra_id_tenant_id="00000000-0000-0000-0000-000000000001",
        entra_id_client_id="client-id-123",
        entra_id_client_secret=b"secret-key-123",
    )
    test_db.add(org)
    await test_db.commit()
    await test_db.refresh(org)
    return org


@pytest.fixture
async def test_user(test_db, test_org):
    """Create test local user"""
    user = User(
        id=uuid4(),
        organization_id=test_org.id,
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


# PKCE Tests
@pytest.mark.asyncio
async def test_pkce_pair_generation():
    """Test PKCE code_verifier and code_challenge generation"""
    code_verifier, code_challenge = EntraIDService._generate_pkce_pair()

    # Verify code_verifier is valid (43-128 chars, no padding)
    assert len(code_verifier) >= 43
    assert len(code_verifier) <= 128
    assert "=" not in code_verifier

    # Verify code_challenge is S256 hash of verifier
    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("utf-8")).digest()
    ).decode("utf-8").rstrip("=")

    assert code_challenge == expected_challenge


@pytest.mark.asyncio
async def test_state_generation():
    """Test CSRF state token generation"""
    state = EntraIDService._generate_state()

    # Should be URL-safe base64
    assert len(state) > 0
    assert "=" not in state  # No padding in URL-safe base64


# Authorization URL Generation Tests
@pytest.mark.asyncio
async def test_generate_authorization_url_success(test_db, test_org):
    """Test successful generation of authorization URL"""
    auth_url, state, error = await EntraIDService.generate_authorization_url(
        db=test_db,
        organization_id=test_org.id,
        redirect_uri="http://localhost:3000/callback",
    )

    assert error is None
    assert auth_url is not None
    assert state is not None
    assert "login.microsoftonline.com" in auth_url
    assert "client_id=client-id-123" in auth_url
    assert f"state={state}" in auth_url
    assert "code_challenge=" in auth_url


@pytest.mark.asyncio
async def test_generate_authorization_url_org_not_found(test_db):
    """Test authorization URL generation with non-existent org"""
    auth_url, state, error = await EntraIDService.generate_authorization_url(
        db=test_db,
        organization_id=uuid4(),
        redirect_uri="http://localhost:3000/callback",
    )

    assert error is not None
    assert "Organization not found" in error
    assert auth_url is None


@pytest.mark.asyncio
async def test_generate_authorization_url_no_entra_config(test_db):
    """Test with org that has no Entra ID configuration"""
    org = Organization(id=uuid4(), name="No Entra Config")
    test_db.add(org)
    await test_db.commit()

    auth_url, state, error = await EntraIDService.generate_authorization_url(
        db=test_db,
        organization_id=org.id,
        redirect_uri="http://localhost:3000/callback",
    )

    assert error is not None
    assert "not configured" in error


# Session Storage Tests
@pytest.mark.asyncio
async def test_session_stored_in_database(test_db, test_org):
    """Test that OAuth session is stored in database"""
    auth_url, state, error = await EntraIDService.generate_authorization_url(
        db=test_db,
        organization_id=test_org.id,
        redirect_uri="http://localhost:3000/callback",
    )

    from sqlalchemy import select

    result = await test_db.execute(
        select(EntraIDSession).where(EntraIDSession.state == state)
    )
    session = result.scalar_one_or_none()

    assert session is not None
    assert session.organization_id == test_org.id
    assert session.state == state
    assert session.code_verifier is not None
    assert session.expires_at > datetime.utcnow()


@pytest.mark.asyncio
async def test_session_expiry(test_db, test_org):
    """Test that sessions expire after configured time"""
    auth_url, state, error = await EntraIDService.generate_authorization_url(
        db=test_db,
        organization_id=test_org.id,
        redirect_uri="http://localhost:3000/callback",
    )

    from sqlalchemy import select

    result = await test_db.execute(
        select(EntraIDSession).where(EntraIDSession.state == state)
    )
    session = result.scalar_one_or_none()

    # Session should expire in 10 minutes (600 seconds)
    expected_expiry = datetime.utcnow() + timedelta(seconds=settings.OAUTH_STATE_EXPIRY)

    # Allow 5 second variation for test execution time
    assert session.expires_at > expected_expiry - timedelta(seconds=5)
    assert session.expires_at < expected_expiry + timedelta(seconds=5)


# User Creation Tests
@pytest.mark.asyncio
async def test_get_or_create_entra_user_new(test_db, test_org):
    """Test creating new user via Entra ID"""
    user, error = await EntraIDService.get_or_create_entra_user(
        db=test_db,
        organization_id=test_org.id,
        email="newuser@example.com",
        entra_id="00000000-0000-0000-0000-000000000002",
        name="New User",
    )

    assert error is None
    assert user is not None
    assert user.email == "newuser@example.com"
    assert user.entra_id == "00000000-0000-0000-0000-000000000002"
    assert user.is_active


@pytest.mark.asyncio
async def test_get_or_create_entra_user_existing_by_id(test_db, test_org):
    """Test retrieving existing user by Entra ID"""
    entra_id = "00000000-0000-0000-0000-000000000002"

    # Create user with Entra ID
    user1, _ = await EntraIDService.get_or_create_entra_user(
        db=test_db,
        organization_id=test_org.id,
        email="user@example.com",
        entra_id=entra_id,
    )

    # Try to get same user again
    user2, error = await EntraIDService.get_or_create_entra_user(
        db=test_db,
        organization_id=test_org.id,
        email="different@example.com",  # Different email
        entra_id=entra_id,  # Same Entra ID
    )

    assert error is None
    assert user2.id == user1.id
    assert user2.email == user1.email  # Email should not change


@pytest.mark.asyncio
async def test_account_linking_on_create(test_db, test_org):
    """Test that existing local user is linked to Entra ID"""
    local_user = User(
        id=uuid4(),
        organization_id=test_org.id,
        email="linked@example.com",
        username="linkeduser",
        is_active=True,
    )
    test_db.add(local_user)
    await test_db.commit()

    # Create Entra user with same email
    user, error = await EntraIDService.get_or_create_entra_user(
        db=test_db,
        organization_id=test_org.id,
        email="linked@example.com",
        entra_id="00000000-0000-0000-0000-000000000003",
    )

    assert error is None
    assert user.id == local_user.id
    assert user.entra_id == "00000000-0000-0000-0000-000000000003"


# Account Linking Tests
@pytest.mark.asyncio
async def test_link_entra_id_success(test_db, test_org, test_user):
    """Test successful account linking"""
    success, error = await EntraIDService.link_entra_id(
        db=test_db,
        user_id=test_user.id,
        entra_id="00000000-0000-0000-0000-000000000004",
        organization_id=test_org.id,
    )

    assert success
    assert error is None

    # Refresh user from DB
    await test_db.refresh(test_user)
    assert test_user.entra_id == "00000000-0000-0000-0000-000000000004"


@pytest.mark.asyncio
async def test_link_entra_id_already_linked(test_db, test_org):
    """Test linking an Entra ID that's already linked to another account"""
    entra_id = "00000000-0000-0000-0000-000000000005"

    # Create two users
    user1 = User(
        id=uuid4(),
        organization_id=test_org.id,
        email="user1@example.com",
        entra_id=entra_id,  # Already linked
    )
    user2 = User(
        id=uuid4(),
        organization_id=test_org.id,
        email="user2@example.com",
    )
    test_db.add(user1)
    test_db.add(user2)
    await test_db.commit()

    # Try to link same Entra ID to user2
    success, error = await EntraIDService.link_entra_id(
        db=test_db,
        user_id=user2.id,
        entra_id=entra_id,
        organization_id=test_org.id,
    )

    assert not success
    assert "already linked" in error.lower()


@pytest.mark.asyncio
async def test_unlink_entra_id_success(test_db, test_org):
    """Test successful account unlinking"""
    user = User(
        id=uuid4(),
        organization_id=test_org.id,
        email="toUnlink@example.com",
        entra_id="00000000-0000-0000-0000-000000000006",
    )
    test_db.add(user)
    await test_db.commit()

    success, error = await EntraIDService.unlink_entra_id(
        db=test_db,
        user_id=user.id,
        organization_id=test_org.id,
    )

    assert success
    assert error is None

    # Refresh and check
    await test_db.refresh(user)
    assert user.entra_id is None


@pytest.mark.asyncio
async def test_unlink_entra_id_not_linked(test_db, test_org, test_user):
    """Test unlinking when user is not linked to Entra ID"""
    # test_user has no entra_id

    success, error = await EntraIDService.unlink_entra_id(
        db=test_db,
        user_id=test_user.id,
        organization_id=test_org.id,
    )

    assert not success
    assert "not linked" in error.lower()


# Error Handling Tests
@pytest.mark.asyncio
async def test_exchange_code_with_expired_state(test_db, test_org):
    """Test code exchange with expired state"""
    # Create expired session
    expired_session = EntraIDSession(
        organization_id=test_org.id,
        state="expired_state",
        code_verifier="verifier",
        expires_at=datetime.utcnow() - timedelta(seconds=10),
    )
    test_db.add(expired_session)
    await test_db.commit()

    user_info, error = await EntraIDService.exchange_code(
        db=test_db,
        organization_id=test_org.id,
        code="auth_code",
        state="expired_state",
    )

    assert user_info is None
    assert "expired" in error.lower()


@pytest.mark.asyncio
async def test_exchange_code_with_invalid_state(test_db, test_org):
    """Test code exchange with invalid state"""
    user_info, error = await EntraIDService.exchange_code(
        db=test_db,
        organization_id=test_org.id,
        code="auth_code",
        state="invalid_state",
    )

    assert user_info is None
    assert "invalid" in error.lower() or "expired" in error.lower()
