from datetime import datetime, UTC, timedelta
import pytest
from sqlalchemy import select
from app.workers.celery_app import celery_app
from app.workers.tasks import record_click_task, cleanup_expired_links_task
from app.database.session import async_session_factory
from app.database.redis import redis_client
from app.models.user import User
from app.models.short_url import ShortURL
from app.models.click_analytics import ClickAnalytics
from app.core.security import hash_password

@pytest.fixture(scope="module", autouse=True)
def celery_eager():
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False

@pytest.fixture
async def test_user_and_url():
    async with async_session_factory() as session:
        user = User(username="task_test_user", email="task_test_user@example.com", password_hash=hash_password("Password123!"))
        session.add(user)
        await session.flush()
        url = ShortURL(original_url="https://google.com", short_code="tasktest", owner_id=user.id, expires_at=datetime.now(UTC) + timedelta(days=1))
        session.add(url)
        await session.commit()
        await session.refresh(url)
        user_id, url_id = user.id, url.id
    yield user_id, url_id
    async with async_session_factory() as session:
        res = await session.get(ShortURL, url_id)
        if res:
            await session.delete(res)
        res_user = await session.get(User, user_id)
        if res_user:
            await session.delete(res_user)
        await session.commit()

@pytest.mark.asyncio
async def test_record_click_task(test_user_and_url):
    _, url_id = test_user_and_url
    record_click_task.delay(url_id=url_id, ip="127.0.0.1", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0", referrer="https://github.com")
    async with async_session_factory() as session:
        url_res = await session.get(ShortURL, url_id)
        assert url_res.clicks == 1
        analytics_res = await session.execute(select(ClickAnalytics).where(ClickAnalytics.url_id == url_id))
        clicks = analytics_res.scalars().all()
        assert len(clicks) == 1
        assert clicks[0].ip == "127.0.0.1"
        assert clicks[0].browser == "Chrome"
        assert clicks[0].device == "Desktop"
        assert clicks[0].os == "Windows"
        assert clicks[0].referrer == "https://github.com"

@pytest.mark.asyncio
async def test_cleanup_expired_links_task(test_user_and_url):
    user_id, _ = test_user_and_url
    async with async_session_factory() as session:
        expired_url = ShortURL(original_url="https://expired.com", short_code="expiredcode", owner_id=user_id, expires_at=datetime.now(UTC) - timedelta(minutes=1), is_active=True)
        session.add(expired_url)
        await session.commit()
        await session.refresh(expired_url)
        expired_id = expired_url.id
    from app.schemas.redirect import CachedURL
    cached = CachedURL(id=expired_id, original_url="https://expired.com", short_code="expiredcode", custom_alias=None, expires_at=datetime.now(UTC) - timedelta(minutes=1), is_active=True, password_hash=None)
    await redis_client.set("url:lookup:expiredcode", cached.model_dump_json())
    cleanup_expired_links_task.delay()
    async with async_session_factory() as session:
        url_db = await session.get(ShortURL, expired_id)
        assert url_db.is_active is False
        assert await redis_client.get("url:lookup:expiredcode") is None
        await session.delete(url_db)
        await session.commit()
