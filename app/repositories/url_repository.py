from typing import Any

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.short_url import ShortURL


class URLRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, url_id: int) -> ShortURL | None:
        result = await self.session.execute(select(ShortURL).where(ShortURL.id == url_id))
        return result.scalar_one_or_none()

    async def get_owned_by_id(self, url_id: int, owner_id: int) -> ShortURL | None:
        result = await self.session.execute(
            select(ShortURL).where(ShortURL.id == url_id, ShortURL.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def get_by_short_code(self, short_code: str) -> ShortURL | None:
        result = await self.session.execute(
            select(ShortURL).where(ShortURL.short_code == short_code)
        )
        return result.scalar_one_or_none()

    async def get_by_short_code_or_alias(self, code_or_alias: str) -> ShortURL | None:
        result = await self.session.execute(
            select(ShortURL).where(
                or_(ShortURL.short_code == code_or_alias, ShortURL.custom_alias == code_or_alias)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_alias(self, alias: str) -> ShortURL | None:
        result = await self.session.execute(
            select(ShortURL).where(ShortURL.custom_alias == alias)
        )
        return result.scalar_one_or_none()

    async def create(self, **values: Any) -> ShortURL:
        url = ShortURL(**values)
        self.session.add(url)
        await self.session.flush()
        await self.session.refresh(url)
        return url

    async def increment_clicks(self, url_id: int) -> None:
        await self.session.execute(
            update(ShortURL)
            .where(ShortURL.id == url_id)
            .values(clicks=ShortURL.clicks + 1, last_accessed_at=func.now())
        )

    async def list_owned(
        self,
        owner_id: int,
        page: int,
        page_size: int,
        search: str | None,
        is_active: bool | None,
        sort: str,
    ) -> tuple[list[ShortURL], int]:
        statement = select(ShortURL).where(ShortURL.owner_id == owner_id)
        count_statement = (
            select(func.count()).select_from(ShortURL).where(ShortURL.owner_id == owner_id)
        )

        if search:
            pattern = f"%{search}%"
            filter_clause = or_(
                ShortURL.original_url.like(pattern),
                ShortURL.short_code.like(pattern),
                ShortURL.custom_alias.like(pattern),
            )
            statement = statement.where(filter_clause)
            count_statement = count_statement.where(filter_clause)

        if is_active is not None:
            statement = statement.where(ShortURL.is_active == is_active)
            count_statement = count_statement.where(ShortURL.is_active == is_active)

        statement = self._apply_sort(statement, sort)
        statement = statement.offset((page - 1) * page_size).limit(page_size)

        total_result = await self.session.execute(count_statement)
        items_result = await self.session.execute(statement)
        return list(items_result.scalars().all()), total_result.scalar_one()

    def _apply_sort(self, statement: Select[tuple[ShortURL]], sort: str) -> Select[tuple[ShortURL]]:
        if sort == "oldest":
            return statement.order_by(ShortURL.created_at.asc())
        if sort == "clicks":
            return statement.order_by(ShortURL.clicks.desc(), ShortURL.created_at.desc())
        return statement.order_by(ShortURL.created_at.desc())
