from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.dependencies.auth import get_current_user
from app.dependencies.rate_limiter import RateLimiter
from app.models.short_url import ShortURL
from app.models.user import User
from app.schemas.url import (
    URLCreateRequest,
    URLListQuery,
    URLListResponse,
    URLResponse,
    URLUpdateRequest,
)
from app.services.url_service import URLService

router = APIRouter(prefix="/urls", tags=["URLs"])


@router.post(
    "",
    response_model=URLResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=20, seconds=60, key_prefix="create_url"))],
)
async def create_url(
    payload: URLCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ShortURL:

    return await URLService(session).create_url(payload=payload, owner=current_user)


@router.get("", response_model=URLListResponse)
async def list_urls(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=255)] = None,
    is_active: bool | None = None,
    sort: Annotated[str, Query(pattern="^(newest|oldest|clicks)$")] = "newest",
) -> URLListResponse:
    query = URLListQuery(
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        sort=sort,
    )
    return await URLService(session).list_urls(owner=current_user, query=query)


@router.get("/popular", response_model=list[URLResponse])
async def get_popular_urls(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[ShortURL]:
    """Return the authenticated user's most-clicked active URLs."""
    statement = (
        select(ShortURL)
        .where(
            ShortURL.owner_id == current_user.id,
            ShortURL.is_active.is_(True),
        )
        .order_by(ShortURL.clicks.desc(), ShortURL.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


@router.get("/{url_id}", response_model=URLResponse)
async def get_url(
    url_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ShortURL:
    return await URLService(session).get_url(url_id=url_id, owner=current_user)


@router.put("/{url_id}", response_model=URLResponse)
async def update_url(
    url_id: int,
    payload: URLUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ShortURL:
    return await URLService(session).update_url(url_id=url_id, payload=payload, owner=current_user)


@router.delete("/{url_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    url_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    await URLService(session).deactivate_url(url_id=url_id, owner=current_user)
