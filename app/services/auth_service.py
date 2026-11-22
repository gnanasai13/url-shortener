from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCredentials, Unauthorized, UserAlreadyExists
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest


class AuthService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.users = UserRepository(session)

    async def register(self, payload: UserRegisterRequest) -> User:
        existing_user = await self.users.get_by_username_or_email(payload.username, payload.email)
        if existing_user:
            raise UserAlreadyExists()

        user = await self.users.create(
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
        )
        await self.session.commit()
        return user

    async def login(self, payload: UserLoginRequest) -> TokenResponse:
        user = await self.users.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise InvalidCredentials()

        token, _token_id, expires_at = create_access_token(str(user.id))
        return TokenResponse(access_token=token, expires_at=expires_at, user=user)

    async def logout(self, token_id: str, expires_at: datetime | None) -> None:
        ttl_seconds = self._seconds_until_expiry(expires_at)
        if ttl_seconds <= 0:
            raise Unauthorized("Token has already expired.")

        await self.redis.setex(f"auth:blacklist:{token_id}", ttl_seconds, "1")

    @staticmethod
    def _seconds_until_expiry(expires_at: datetime | None) -> int:
        if expires_at is None:
            return 0
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return int((expires_at - datetime.now(UTC)).total_seconds())
