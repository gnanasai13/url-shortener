import re
from datetime import UTC, datetime
from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_validator
ALIAS_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")

class URLCreateRequest(BaseModel):
    original_url: AnyUrl
    custom_alias: str | None = Field(default=None, min_length=3, max_length=64)
    expires_at: datetime | None = None
    is_active: bool = True
    password: str | None = Field(default=None, min_length=8, max_length=128)
    @field_validator("custom_alias")
    @classmethod
    def validate_alias(cls, value: str | None) -> str | None:
        if value is not None and not ALIAS_PATTERN.fullmatch(value):
            raise ValueError("Alias may contain only letters, numbers, hyphens, and underscores.")
        return value
    @field_validator("original_url")
    @classmethod
    def validate_original_url(cls, value: AnyUrl) -> AnyUrl:
        if value.scheme.lower() not in {"http", "https"}:
            raise ValueError("Only HTTP and HTTPS destination URLs are supported.")
        return value
    @field_validator("expires_at")
    @classmethod
    def validate_expiration(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            expiration = value if value.tzinfo else value.replace(tzinfo=UTC)
            if expiration <= datetime.now(UTC):
                raise ValueError("Expiration date must be in the future.")
        return value

class URLUpdateRequest(BaseModel):
    original_url: AnyUrl | None = None
    custom_alias: str | None = Field(default=None, min_length=3, max_length=64)
    expires_at: datetime | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    @field_validator("custom_alias")
    @classmethod
    def validate_alias(cls, value: str | None) -> str | None:
        if value is not None and not ALIAS_PATTERN.fullmatch(value):
            raise ValueError("Alias may contain only letters, numbers, hyphens, and underscores.")
        return value
    @field_validator("original_url")
    @classmethod
    def validate_original_url(cls, value: AnyUrl | None) -> AnyUrl | None:
        if value is not None and value.scheme.lower() not in {"http", "https"}:
            raise ValueError("Only HTTP and HTTPS destination URLs are supported.")
        return value
    @field_validator("expires_at")
    @classmethod
    def validate_expiration(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            expiration = value if value.tzinfo else value.replace(tzinfo=UTC)
            if expiration <= datetime.now(UTC):
                raise ValueError("Expiration date must be in the future.")
        return value

class URLListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    sort: str = Field(default="newest", pattern="^(newest|oldest|clicks)$")

class URLResponse(BaseModel):
    id: int
    original_url: str
    short_code: str
    custom_alias: str | None
    clicks: int
    expires_at: datetime | None
    is_active: bool
    owner_id: int
    created_at: datetime
    last_accessed_at: datetime | None
    model_config = ConfigDict(from_attributes=True)

class URLListResponse(BaseModel):
    items: list[URLResponse]
    total: int
    page: int
    page_size: int
