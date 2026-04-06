"""
Example: Testing Patterns
===========================
Reference implementation of pytest-asyncio test fixtures, async test client,
factories, mocking patterns, and database test setup.

Location: tests/conftest.py (shared fixtures)
         tests/unit/modules/<module>/test_service.py (unit tests)
         tests/integration/modules/<module>/test_router.py (integration tests)
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base
from app.core.dependencies import get_db
from app.core.security import hash_password
from app.main import create_app


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION (tests/conftest.py)
# ═══════════════════════════════════════════════════════════════════════════════


# Use in-memory SQLite for fast, isolated tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION-SCOPED FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session.

    Required for session-scoped async fixtures.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCTION-SCOPED FIXTURES (fresh per test)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test.

    - Creates all tables before the test.
    - Drops all tables after the test (clean slate).
    - Each test is fully isolated.
    """
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Yield session
    async with TestSessionLocal() as session:
        yield session

    # Cleanup
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with DB dependency overridden.

    Usage:
        async def test_create_user(client: AsyncClient):
            response = await client.post("/api/v1/users/", json={...})
            assert response.status_code == 201
    """
    app = create_app()

    # Override DB dependency to use test session
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    # Clean up overrides
    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORIES — Create test data with sensible defaults
# ═══════════════════════════════════════════════════════════════════════════════


class UserFactory:
    """Factory for creating User test data.

    Usage:
        # Create data dict for API requests
        user_data = UserFactory.build()

        # Create user in DB
        user = await UserFactory.create(db_session)

        # Custom overrides
        admin = await UserFactory.create(db_session, role="admin")
    """

    _counter: int = 0

    @classmethod
    def build(cls, **overrides: Any) -> dict[str, Any]:
        """Build a user data dict (for API requests)."""
        cls._counter += 1
        defaults = {
            "email": f"user{cls._counter}@example.com",
            "full_name": f"Test User {cls._counter}",
            "password": "SecurePass123",
        }
        defaults.update(overrides)
        return defaults

    @classmethod
    async def create(cls, session: AsyncSession, **overrides: Any) -> Any:
        """Create and persist a User in the database."""
        from app.modules.users.models import User

        cls._counter += 1
        defaults = {
            "email": f"user{cls._counter}@example.com",
            "full_name": f"Test User {cls._counter}",
            "hashed_password": hash_password("SecurePass123"),
            "role": "user",
            "is_active": True,
        }
        defaults.update(overrides)

        user = User(**defaults)
        session.add(user)
        await session.flush()
        await session.refresh(user)
        return user

    @classmethod
    def reset(cls) -> None:
        """Reset the counter (call in session-scoped fixture if needed)."""
        cls._counter = 0


class ItemFactory:
    """Factory for creating Item test data."""

    _counter: int = 0

    @classmethod
    def build(cls, owner_id: UUID | None = None, **overrides: Any) -> dict[str, Any]:
        """Build an item data dict."""
        cls._counter += 1
        defaults = {
            "title": f"Test Item {cls._counter}",
            "description": f"Description for item {cls._counter}",
            "status": "draft",
        }
        if owner_id:
            defaults["owner_id"] = str(owner_id)
        defaults.update(overrides)
        return defaults

    @classmethod
    async def create(
        cls, session: AsyncSession, owner_id: UUID, **overrides: Any
    ) -> Any:
        """Create and persist an Item in the database."""
        from app.modules.items.models import Item

        cls._counter += 1
        defaults = {
            "title": f"Test Item {cls._counter}",
            "description": f"Description for item {cls._counter}",
            "status": "draft",
            "owner_id": owner_id,
        }
        defaults.update(overrides)

        item = Item(**defaults)
        session.add(item)
        await session.flush()
        await session.refresh(item)
        return item


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def authenticated_client(
    client: AsyncClient, db_session: AsyncSession
) -> AsyncClient:
    """Provide a client with a valid auth token.

    Creates a test user and injects the Authorization header.
    """
    from app.core.security import create_access_token

    user = await UserFactory.create(db_session)
    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role})
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def admin_client(
    client: AsyncClient, db_session: AsyncSession
) -> AsyncClient:
    """Provide a client with admin role auth token."""
    from app.core.security import create_access_token

    admin = await UserFactory.create(db_session, role="admin")
    token = create_access_token(
        subject=str(admin.id), extra_claims={"role": "admin"}
    )
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE: INTEGRATION TESTS (tests/integration/modules/users/test_router.py)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreateUser:
    """Integration tests for POST /api/v1/users/."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, client: AsyncClient) -> None:
        """Test successful user creation."""
        user_data = UserFactory.build()

        response = await client.post("/api/v1/users/", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data
        assert "password" not in data  # Never expose passwords

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, client: AsyncClient) -> None:
        """Test that duplicate emails return 409 Conflict."""
        user_data = UserFactory.build()

        # First creation succeeds
        response1 = await client.post("/api/v1/users/", json=user_data)
        assert response1.status_code == 201

        # Second creation fails
        response2 = await client.post("/api/v1/users/", json=user_data)
        assert response2.status_code == 409
        assert response2.json()["error"]["code"] == "CONFLICT"

    @pytest.mark.asyncio
    async def test_create_user_invalid_email(self, client: AsyncClient) -> None:
        """Test that invalid email format returns 422."""
        user_data = UserFactory.build(email="not-an-email")

        response = await client.post("/api/v1/users/", json=user_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user_weak_password(self, client: AsyncClient) -> None:
        """Test that weak passwords are rejected."""
        user_data = UserFactory.build(password="weak")

        response = await client.post("/api/v1/users/", json=user_data)

        assert response.status_code == 422


class TestGetUser:
    """Integration tests for GET /api/v1/users/{user_id}."""

    @pytest.mark.asyncio
    async def test_get_user_success(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test fetching an existing user."""
        user = await UserFactory.create(db_session)

        response = await authenticated_client.get(f"/api/v1/users/{user.id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(user.id)

    @pytest.mark.asyncio
    async def test_get_user_not_found(
        self, authenticated_client: AsyncClient
    ) -> None:
        """Test fetching a non-existent user returns 404."""
        fake_id = uuid4()

        response = await authenticated_client.get(f"/api/v1/users/{fake_id}")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_user_unauthenticated(self, client: AsyncClient) -> None:
        """Test that unauthenticated requests return 401."""
        response = await client.get(f"/api/v1/users/{uuid4()}")

        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE: UNIT TESTS (tests/unit/modules/users/test_service.py)
# ═══════════════════════════════════════════════════════════════════════════════


class TestUserService:
    """Unit tests for UserService — mock the repository."""

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self) -> None:
        """Test that service raises NotFoundError for missing user."""
        from unittest.mock import AsyncMock

        from app.core.exceptions import NotFoundError
        from app.modules.users.service import UserService

        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        service = UserService(repository=mock_repo)

        # Act & Assert
        with pytest.raises(NotFoundError):
            await service.get_by_id(uuid4())

        mock_repo.get_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self) -> None:
        """Test that creating a user with existing email raises ConflictError."""
        from unittest.mock import AsyncMock, MagicMock

        from app.core.exceptions import ConflictError
        from app.modules.users.schemas import UserCreate
        from app.modules.users.service import UserService

        # Arrange
        mock_repo = AsyncMock()
        mock_repo.get_by_email.return_value = MagicMock()  # User exists
        service = UserService(repository=mock_repo)

        user_data = UserCreate(
            email="test@example.com",
            full_name="Test User",
            password="SecurePass123",
        )

        # Act & Assert
        with pytest.raises(ConflictError):
            await service.create(user_data)
