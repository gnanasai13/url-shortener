from collections.abc import AsyncGenerator
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.database.base import Base
from app.database.session import get_db_session
from app.models.user import User
from app.core.security import hash_password, create_access_token
from app.database.redis import redis_client

# Use SQLite in-memory for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

test_async_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session_factory() as session:
        yield session
        # Clear tables to isolate tests from each other
        async with test_engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())
            await conn.commit()


@pytest.fixture(autouse=True)
async def override_db_dependency(db_session):
    async def _get_test_db():
        yield db_session
    app.dependency_overrides[get_db_session] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db_session, None)


@pytest.fixture(autouse=True)
async def clear_redis_keys():
    # Clear rate limiters and lookups
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match="*")
        if keys:
            await redis_client.delete(*keys)
        if cursor == 0:
            break
    yield


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(db_session) -> User:
    user = User(
        username="crud_test_user",
        email="crud_test_user@example.com",
        password_hash=hash_password("Password123!"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user) -> dict[str, str]:
    token, _, _ = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}
