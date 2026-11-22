import asyncio
from datetime import datetime, UTC
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.database.session import async_session_factory
from app.database.redis import redis_client
from app.models.short_url import ShortURL
from app.services.analytics_service import AnalyticsService
from app.services.redirect_service import RedirectService

logger = get_task_logger(__name__)


@celery_app.task(name="app.workers.tasks.record_click_task")
def record_click_task(
    url_id: int,
    ip: str | None,
    user_agent: str | None,
    referrer: str | None,
) -> None:
    logger.info("processing_click_event_for_url", url_id=url_id)

    async def _run() -> None:
        await AnalyticsService.record_click(
            url_id=url_id,
            ip=ip,
            user_agent=user_agent,
            referrer=referrer,
        )

    asyncio.run(_run())


@celery_app.task(name="app.workers.tasks.cleanup_expired_links_task")
def cleanup_expired_links_task() -> None:
    logger.info("running_expired_links_cleanup")

    async def _run() -> None:
        async with async_session_factory() as session:
            statement = select(ShortURL).where(
                ShortURL.expires_at <= datetime.now(UTC),
                ShortURL.is_active == True,
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

    asyncio.run(_run())
