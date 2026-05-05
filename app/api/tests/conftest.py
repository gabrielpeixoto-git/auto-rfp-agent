import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.infrastructure.database.connection import Base, get_db
from src.core.config import settings

# Test database
TEST_DATABASE_URL = settings.database_url.replace(
    settings.database_url.split('/')[-1],
    "test_autorfpdb"
)

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create test database tables and yield session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(client):
    """Create test user and return with token."""
    # First create tenant
    tenant_response = await client.post("/api/v1/auth/tenants", json={"name": "Test Tenant"})
    tenant_id = tenant_response.json()["id"]

    # Create user
    user_data = {
        "email": "test@example.com",
        "password": "password123",
        "role": "admin",
        "tenant_id": tenant_id,
    }
    response = await client.post("/api/v1/auth/register", json=user_data)
    return response.json()


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Return authorization headers for test user."""
    return {"Authorization": f"Bearer {test_user['access_token']}"}


@pytest_asyncio.fixture
async def test_project(client, auth_headers):
    """Create a test project and return it."""
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "description": "Test project for testing"},
        headers=auth_headers
    )
    return response.json()
