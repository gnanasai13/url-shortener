import pytest
from datetime import datetime, UTC, timedelta
from httpx import AsyncClient
from app.models.short_url import ShortURL
from app.workers.celery_app import celery_app
from app.core.security import hash_password

@pytest.fixture(scope="module", autouse=True)
def celery_eager():
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False

@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient, test_user, db_session):
    url = ShortURL(original_url="https://google.com", short_code="gcode", owner_id=test_user.id, is_active=True)
    db_session.add(url)
    await db_session.commit()
    response = await client.get("/gcode", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://google.com"

@pytest.mark.asyncio
async def test_redirect_expired(client: AsyncClient, test_user, db_session):
    url = ShortURL(original_url="https://google.com", short_code="expiredcode", owner_id=test_user.id, is_active=True, expires_at=datetime.now(UTC) - timedelta(minutes=10))
    db_session.add(url)
    await db_session.commit()
    response = await client.get("/expiredcode")
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "expired_url"

@pytest.mark.asyncio
async def test_redirect_inactive(client: AsyncClient, test_user, db_session):
    url = ShortURL(original_url="https://google.com", short_code="inactivecode", owner_id=test_user.id, is_active=False)
    db_session.add(url)
    await db_session.commit()
    response = await client.get("/inactivecode")
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "inactive_url"

@pytest.mark.asyncio
async def test_redirect_password_protected(client: AsyncClient, test_user, db_session):
    url = ShortURL(original_url="https://google.com", short_code="lockedcode", owner_id=test_user.id, is_active=True, password_hash=hash_password("secure_pw"))
    db_session.add(url)
    await db_session.commit()
    response = await client.get("/lockedcode")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "link_password_required"
    response = await client.get("/lockedcode?password=wrong_pw")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_link_password"
    response = await client.get("/lockedcode?password=secure_pw")
    assert response.status_code == 307
    assert response.headers["location"] == "https://google.com"
