from datetime import datetime
from pydantic import BaseModel, ConfigDict

class CountBucket(BaseModel):
    name: str
    count: int

class DailyClickBucket(BaseModel):
    date: str
    count: int

class RecentClick(BaseModel):
    id: int
    ip: str | None
    browser: str | None
    device: str | None
    os: str | None
    referrer: str | None
    country: str | None
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class URLAnalyticsResponse(BaseModel):
    url_id: int
    short_code: str
    custom_alias: str | None
    original_url: str
    total_clicks: int
    stored_click_events: int
    created_at: datetime
    last_accessed_at: datetime | None
    daily_clicks: list[DailyClickBucket]
    browsers: list[CountBucket]
    devices: list[CountBucket]
    operating_systems: list[CountBucket]
    countries: list[CountBucket]
    referrers: list[CountBucket]
    recent_clicks: list[RecentClick]
