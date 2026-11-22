from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.database.redis import redis_client
from app.database.session import async_session_factory
from app.models.click_analytics import ClickAnalytics
from app.models.short_url import ShortURL
from app.models.user import User
from app.schemas.redirect import CachedURL
from app.workers.tasks import record_click, cleanup_expired_links


@pytest.fixture
async def test_user_and_url():
    async with async_session_factory() as session:
        user = User(
            username="task_test_user",
            email="task_test_user@example.com",
            password_hash=hash_password("Password123!"),
        )
        session.add(user)
        await session.flush()

        url = ShortURL(
            original_url="https://google.com",
            short_code="tasktest",
            owner_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        session.add(url)
        await session.commit()
        await session.refresh(url)
        user_id, url_id = user.id, url.id

    yield user_id, url_id

    async with async_session_factory() as session:
        url_record = await session.get(ShortURL, url_id)
        if url_record:
            await session.delete(url_record)
        user_record = await session.get(User, user_id)
        if user_record:
            await session.delete(user_record)
        await session.commit()


@pytest.mark.asyncio
async def test_record_click_task(test_user_and_url):
    _, url_id = test_user_and_url
    await record_click(
        url_id=url_id,
        ip="127.0.0.1",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        referrer="https://github.com",
    )

    async with async_session_factory() as session:
        url_record = await session.get(ShortURL, url_id)
        assert url_record.clicks == 1

        result = await session.execute(
            select(ClickAnalytics).where(ClickAnalytics.url_id == url_id)
        )
        clicks = result.scalars().all()
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
        expired_url = ShortURL(
            original_url="https://expired.com",
            short_code="expiredcode",
            owner_id=user_id,
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
            is_active=True,
        )
        session.add(expired_url)
        await session.commit()
        await session.refresh(expired_url)
        expired_id = expired_url.id

    cached = CachedURL(
        id=expired_id,
        original_url="https://expired.com",
        short_code="expiredcode",
        custom_alias=None,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
        is_active=True,
        password_hash=None,
    )
    await redis_client.set("url:lookup:expiredcode", cached.model_dump_json())

    await cleanup_expired_links()

    async with async_session_factory() as session:
        url_record = await session.get(ShortURL, expired_id)
        assert url_record.is_active is False
        assert await redis_client.get("url:lookup:expiredcode") is None
        await session.delete(url_record)
        await session.commit()
