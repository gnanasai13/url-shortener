from app.database.session import async_session_factory
from app.models.user import User
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.url_repository import URLRepository
from app.schemas.analytics import CountBucket, DailyClickBucket, URLAnalyticsResponse
from app.core.exceptions import URLNotFound


class AnalyticsService:
    def __init__(self, session) -> None:
        self.session = session
        self.urls = URLRepository(session)
        self.analytics = AnalyticsRepository(session)

    async def get_url_analytics(self, url_id: int, owner: User) -> URLAnalyticsResponse:
        url = await self.urls.get_owned_by_id(url_id=url_id, owner_id=owner.id)
        if url is None:
            raise URLNotFound()

        stored_click_events = await self.analytics.count_clicks(url_id)
        daily_clicks = await self.analytics.daily_clicks(url_id)
        browsers = await self.analytics.breakdown(url_id, "browser")
        devices = await self.analytics.breakdown(url_id, "device")
        operating_systems = await self.analytics.breakdown(url_id, "os")
        countries = await self.analytics.breakdown(url_id, "country")
        referrers = await self.analytics.breakdown(url_id, "referrer")
        recent_clicks = await self.analytics.recent_clicks(url_id)

        return URLAnalyticsResponse(
            url_id=url.id,
            short_code=url.short_code,
            custom_alias=url.custom_alias,
            original_url=url.original_url,
            total_clicks=url.clicks,
            stored_click_events=stored_click_events,
            created_at=url.created_at,
            last_accessed_at=url.last_accessed_at,
            daily_clicks=[
                DailyClickBucket(date=day, count=count) for day, count in daily_clicks
            ],
            browsers=[CountBucket(name=name, count=count) for name, count in browsers],
            devices=[CountBucket(name=name, count=count) for name, count in devices],
            operating_systems=[
                CountBucket(name=name, count=count) for name, count in operating_systems
            ],
            countries=[CountBucket(name=name, count=count) for name, count in countries],
            referrers=[CountBucket(name=name, count=count) for name, count in referrers],
            recent_clicks=recent_clicks,
        )

    @staticmethod
    async def record_click(
        url_id: int,
        ip: str | None,
        user_agent: str | None,
        referrer: str | None,
    ) -> None:
        browser, device, os = AnalyticsService._parse_user_agent(user_agent)

        async with async_session_factory() as session:
            urls = URLRepository(session)
            analytics = AnalyticsRepository(session)
            await urls.increment_clicks(url_id)
            await analytics.create_click(
                url_id=url_id,
                ip=ip,
                browser=browser,
                device=device,
                os=os,
                referrer=referrer,
            )
            await session.commit()

    @staticmethod
    def _parse_user_agent(user_agent: str | None) -> tuple[str | None, str | None, str | None]:
        if not user_agent:
            return None, None, None

        lowered = user_agent.lower()
        browser = "Chrome" if "chrome" in lowered else None
        if "firefox" in lowered:
            browser = "Firefox"
        elif "safari" in lowered and "chrome" not in lowered:
            browser = "Safari"
        elif "edg" in lowered:
            browser = "Edge"

        device = (
            "Mobile"
            if any(token in lowered for token in ["mobile", "android", "iphone"])
            else "Desktop"
        )

        os = None
        if "windows" in lowered:
            os = "Windows"
        elif "mac os" in lowered or "macintosh" in lowered:
            os = "macOS"
        elif "linux" in lowered:
            os = "Linux"
        elif "android" in lowered:
            os = "Android"
        elif "iphone" in lowered or "ipad" in lowered:
            os = "iOS"

        return browser, device, os
