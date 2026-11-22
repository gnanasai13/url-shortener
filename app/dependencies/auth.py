from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Unauthorized
from app.core.security import decode_access_token
from app.database.redis import redis_client
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    if credentials is None:
        raise Unauthorized()

    payload = decode_access_token(credentials.credentials)
    token_id = payload["jti"]

    if await redis_client.exists(f"auth:blacklist:{token_id}"):
        raise Unauthorized("Access token has been logged out.")

    user = await UserRepository(session).get_by_id(int(payload["sub"]))
    if user is None:
        raise Unauthorized("Token user no longer exists.")

    return user


async def get_current_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, str]:
    if credentials is None:
        raise Unauthorized()
    return decode_access_token(credentials.credentials)


def get_token_expiry(payload: dict[str, str]) -> datetime | None:
    exp = payload.get("exp")
    if exp is None:
        return None
    return datetime.fromtimestamp(int(exp), tz=UTC)
