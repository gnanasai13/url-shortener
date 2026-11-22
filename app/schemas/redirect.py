from datetime import datetime
from pydantic import BaseModel

class CachedURL(BaseModel):
    id: int
    original_url: str
    short_code: str
    custom_alias: str | None
    expires_at: datetime | None
    is_active: bool
    password_hash: str | None
