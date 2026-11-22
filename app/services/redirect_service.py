from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ExpiredURL,
    InactiveURL,
    InvalidLinkPassword,
    LinkPasswordRequired,
    URLNotFound,
)
from app.core.security import verify_password
from app.models.short_url import ShortURL
from app.repositories.url_repository import URLRepository
from app.schemas.redirect import CachedURL


class RedirectService:
    cache_ttl_seconds = 300

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.urls = URLRepository(session)

    async def resolve_url(self, code_or_alias: str, password: str | None) -> CachedURL:
        cached_url = await self._get_cached_url(code_or_alias)
        if cached_url is None:
            url = await self.urls.get_by_short_code_or_alias(code_or_alias)
            if url is None:
                raise URLNotFound()
            cached_url = self._to_cached_url(url)
            await self._cache_url(cached_url)

        self._ensure_redirect_allowed(cached_url, password)
        return cached_url

    async def invalidate_cache(self, short_code: str, custom_alias: str | None = None) -> None:
        keys = [self._cache_key(short_code)]
        if custom_alias:
            keys.append(self._cache_key(custom_alias))
        await self.redis.delete(*keys)

    def _ensure_redirect_allowed(self, url: CachedURL, password: str | None) -> None:
        if not url.is_active:
            raise InactiveURL()

        if url.expires_at:
            expires_at = (
                url.expires_at
                if url.expires_at.tzinfo
                else url.expires_at.replace(tzinfo=UTC)
            )
            if expires_at <= datetime.now(UTC):
                raise ExpiredURL()

        if url.password_hash:
            if not password:
                raise LinkPasswordRequired()
            if not verify_password(password, url.password_hash):
                raise InvalidLinkPassword()

    async def _get_cached_url(self, code_or_alias: str) -> CachedURL | None:
        value = await self.redis.get(self._cache_key(code_or_alias))
        if value is None:
            return None
        return CachedURL.model_validate_json(value)

    async def _cache_url(self, url: CachedURL) -> None:
        payload = url.model_dump_json()
        await self.redis.setex(self._cache_key(url.short_code), self.cache_ttl_seconds, payload)
        if url.custom_alias:
            await self.redis.setex(
                self._cache_key(url.custom_alias),
                self.cache_ttl_seconds,
                payload,
            )

    @staticmethod
    def _to_cached_url(url: ShortURL) -> CachedURL:
        return CachedURL(
            id=url.id,
            original_url=url.original_url,
            short_code=url.short_code,
            custom_alias=url.custom_alias,
            expires_at=url.expires_at,
            is_active=url.is_active,
            password_hash=url.password_hash,
        )

    @staticmethod
    def _cache_key(code_or_alias: str) -> str:
        return f"url:lookup:{code_or_alias}"
