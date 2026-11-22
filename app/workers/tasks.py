import asyncio
from datetime import UTC, datetime

from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.database.redis import redis_client
from app.database.session import async_session_factory
from app.models.short_url import ShortURL
from app.services.analytics_service import AnalyticsService
from app.services.redirect_service import RedirectService
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


async def record_click(
    url_id: int,
    ip: str | None,
    user_agent: str | None,
    referrer: str | None,
) -> None:
    """Persist a click event; separated for direct async testing."""
    await AnalyticsService.record_click(
        url_id=url_id,
        ip=ip,
        user_agent=user_agent,
        referrer=referrer,
    )


async def cleanup_expired_links() -> None:
    """Deactivate expired links and invalidate their redirect cache entries."""
    async with async_session_factory() as session:
        statement = select(ShortURL).where(
            ShortURL.expires_at <= datetime.now(UTC),
            ShortURL.is_active.is_(True),
        )
        result = await session.execute(statement)
        expired_urls = result.scalars().all()

        if not expired_urls:
            logger.info("no_expired_links_found")
            return

        redirect_service = RedirectService(session, redis_client)
        for url in expired_urls:
            url.is_active = False
            await redirect_service.invalidate_cache(url.short_code, url.custom_alias)

        await session.commit()
        logger.info("expired_links_cleaned_up", count=len(expired_urls))


@celery_app.task(name="app.workers.tasks.record_click_task")
def record_click_task(
    url_id: int,
    ip: str | None,
    user_agent: str | None,
    referrer: str | None,
) -> None:
    logger.info("processing_click_event_for_url", url_id=url_id)
    asyncio.run(record_click(url_id, ip, user_agent, referrer))


@celery_app.task(name="app.workers.tasks.cleanup_expired_links_task")
def cleanup_expired_links_task() -> None:
    logger.info("running_expired_links_cleanup")
    asyncio.run(cleanup_expired_links())
