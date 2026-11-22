from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "URL Shortener API"
    app_env: Literal["local", "dev", "staging", "production", "test"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_user: str = "url_shortener"
    mysql_password: str = "url_shortener_password"
    mysql_database: str = "url_shortener"

    database_url: str = Field(
        default="mysql+asyncmy://url_shortener:url_shortener_password@mysql:3306/url_shortener"
    )

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_url: str = "redis://redis:6379/0"

    jwt_secret_key: str = "change-me-before-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
