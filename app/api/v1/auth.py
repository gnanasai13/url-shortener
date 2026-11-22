from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.redis import redis_client
from app.database.session import get_db_session
from app.dependencies.auth import get_current_token_payload, get_current_user, get_token_expiry
from app.dependencies.rate_limiter import RateLimiter
from app.models.user import User
from app.schemas.auth import (
    LogoutResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=5, seconds=60, key_prefix="register"))],
)
async def register(
    payload: UserRegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    return await AuthService(session=session, redis=redis_client).register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60, key_prefix="login"))],
)
async def login(
    payload: UserLoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:

    return await AuthService(session=session, redis=redis_client).login(payload)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    token_payload: Annotated[dict[str, str], Depends(get_current_token_payload)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LogoutResponse:
    service = AuthService(session=session, redis=redis_client)
    await service.logout(token_id=token_payload["jti"], expires_at=get_token_expiry(token_payload))
    return LogoutResponse(message=f"User {current_user.id} logged out successfully.")
