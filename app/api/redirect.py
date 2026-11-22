from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database.redis import redis_client
from app.database.session import get_db_session
from app.dependencies.rate_limiter import RateLimiter
from app.services.redirect_service import RedirectService
from app.workers.tasks import record_click_task

router = APIRouter(tags=["Redirect"])
logger = get_logger(__name__)


@router.get(
    "/{short_code}",
    include_in_schema=False,
    dependencies=[Depends(RateLimiter(times=100, seconds=60, key_prefix="redirect"))],
)
async def redirect_short_url(
    short_code: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    password: Annotated[str | None, Query(max_length=128)] = None,
) -> RedirectResponse:
    cached_url = await RedirectService(session=session, redis=redis_client).resolve_url(
        code_or_alias=short_code,
        password=password,
    )

    try:
        record_click_task.delay(
            url_id=cached_url.id,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            referrer=request.headers.get("referer"),
        )
    except Exception:
        # A temporary queue outage must not prevent the user's redirect.
        logger.exception("click_event_enqueue_failed", url_id=cached_url.id)

    return RedirectResponse(url=cached_url.original_url, status_code=307)
