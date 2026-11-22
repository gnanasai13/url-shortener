from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Select, func, select

from app.models.click_analytics import ClickAnalytics


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_click(
        self,
        url_id: int,
        ip: str | None,
        browser: str | None,
        device: str | None,
        os: str | None,
        referrer: str | None,
        country: str | None = None,
    ) -> ClickAnalytics:
        click = ClickAnalytics(
            url_id=url_id,
            ip=ip,
            browser=browser,
            device=device,
            os=os,
            referrer=referrer,
            country=country,
        )
        self.session.add(click)
        await self.session.flush()
        return click

    async def count_clicks(self, url_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(ClickAnalytics).where(ClickAnalytics.url_id == url_id)
        )
        return result.scalar_one()

    async def daily_clicks(self, url_id: int) -> list[tuple[str, int]]:
        day = func.date(ClickAnalytics.timestamp)
        result = await self.session.execute(
            select(day.label("day"), func.count().label("count"))
            .where(ClickAnalytics.url_id == url_id)
            .group_by(day)
            .order_by(day.asc())
        )
        return [(str(row.day), row.count) for row in result.all()]

    async def breakdown(self, url_id: int, field: str) -> list[tuple[str, int]]:
        column = getattr(ClickAnalytics, field)
        label = func.coalesce(column, "Unknown")
        result = await self.session.execute(
            select(label.label("name"), func.count().label("count"))
            .where(ClickAnalytics.url_id == url_id)
            .group_by(label)
            .order_by(func.count().desc())
        )
        return [(row.name, row.count) for row in result.all()]

    async def recent_clicks(self, url_id: int, limit: int = 20) -> list[ClickAnalytics]:
        result = await self.session.execute(
            self._recent_clicks_statement(url_id=url_id).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def _recent_clicks_statement(url_id: int) -> Select[tuple[ClickAnalytics]]:
        return (
            select(ClickAnalytics)
            .where(ClickAnalytics.url_id == url_id)
            .order_by(ClickAnalytics.timestamp.desc())
        )
