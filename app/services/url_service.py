from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AliasAlreadyExists, InvalidURLUpdate, URLNotFound
from app.core.security import hash_password
from app.database.redis import redis_client
from app.models.short_url import ShortURL
from app.models.user import User
from app.repositories.url_repository import URLRepository
from app.schemas.url import URLCreateRequest, URLListQuery, URLListResponse, URLUpdateRequest
from app.services.redirect_service import RedirectService
from app.utils.short_code import generate_short_code


class URLService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.urls = URLRepository(session)

    async def create_url(self, payload: URLCreateRequest, owner: User) -> ShortURL:
        if payload.custom_alias:
            await self._ensure_alias_available(payload.custom_alias)

        short_code = await self._generate_unique_short_code()
        url = await self.urls.create(
            original_url=str(payload.original_url),
            short_code=short_code,
            custom_alias=payload.custom_alias,
            expires_at=payload.expires_at,
            is_active=payload.is_active,
            password_hash=hash_password(payload.password) if payload.password else None,
            owner_id=owner.id,
        )
        await self.session.commit()
        return url

    async def list_urls(self, owner: User, query: URLListQuery) -> URLListResponse:
        items, total = await self.urls.list_owned(
            owner_id=owner.id,
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            is_active=query.is_active,
            sort=query.sort,
        )
        return URLListResponse(items=items, total=total, page=query.page, page_size=query.page_size)

    async def get_url(self, url_id: int, owner: User) -> ShortURL:
        url = await self.urls.get_owned_by_id(url_id=url_id, owner_id=owner.id)
        if url is None:
            raise URLNotFound()
        return url

    async def update_url(self, url_id: int, payload: URLUpdateRequest, owner: User) -> ShortURL:
        url = await self.get_url(url_id=url_id, owner=owner)
        old_short_code = url.short_code
        old_custom_alias = url.custom_alias
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise InvalidURLUpdate()

        if "custom_alias" in updates and payload.custom_alias != url.custom_alias:
            if payload.custom_alias is not None:
                await self._ensure_alias_available(payload.custom_alias)
            url.custom_alias = payload.custom_alias

        if "original_url" in updates and payload.original_url is not None:
            url.original_url = str(payload.original_url)
        if "expires_at" in updates:
            url.expires_at = payload.expires_at
        if "is_active" in updates:
            url.is_active = bool(payload.is_active)
        if "password" in updates:
            url.password_hash = hash_password(payload.password) if payload.password else None

        await self.session.commit()
        await self.session.refresh(url)
        redirect_service = RedirectService(self.session, redis_client)
        await redirect_service.invalidate_cache(old_short_code, old_custom_alias)
        await redirect_service.invalidate_cache(url.short_code, url.custom_alias)
        return url

    async def deactivate_url(self, url_id: int, owner: User) -> None:
        url = await self.get_url(url_id=url_id, owner=owner)
        url.is_active = False
        await self.session.commit()
        await RedirectService(self.session, redis_client).invalidate_cache(
            url.short_code,
            url.custom_alias,
        )

    async def _ensure_alias_available(self, alias: str) -> None:
        if await self.urls.get_by_alias(alias):
            raise AliasAlreadyExists()
        if await self.urls.get_by_short_code(alias):
            raise AliasAlreadyExists("This alias conflicts with an existing short code.")

    async def _generate_unique_short_code(self) -> str:
        for _ in range(10):
            short_code = generate_short_code()
            if await self.urls.get_by_short_code(short_code) is None:
                return short_code
        raise AliasAlreadyExists("Unable to generate a unique short code. Please retry.")
