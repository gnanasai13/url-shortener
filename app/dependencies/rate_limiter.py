import time
import uuid
from fastapi import Request

from app.core.exceptions import RateLimitExceeded
from app.database.redis import redis_client


class RateLimiter:
    def __init__(self, times: int, seconds: int, key_prefix: str = "rl") -> None:
        self.times = times
        self.seconds = seconds
        self.key_prefix = key_prefix

    async def __call__(self, request: Request) -> None:
        # Resolve identifier
        identifier = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            from app.core.security import decode_access_token
            try:
                token = auth_header.split(" ")[1]
                payload = decode_access_token(token)
                identifier = f"user:{payload['sub']}"
            except Exception:
                pass

        if not identifier:
            # Do not trust X-Forwarded-For from arbitrary clients: it can be
            # forged to rotate rate-limit identities. Configure trusted proxy
            # handling at the ASGI/server layer before using forwarded headers.
            identifier = f"ip:{request.client.host if request.client else 'unknown'}"

        key = f"rate_limit:{self.key_prefix}:{identifier}"
        now = time.time()
        clear_before = now - self.seconds
        member = f"{now}:{uuid.uuid4()}"

        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, clear_before)
            pipe.zcard(key)
            pipe.zadd(key, {member: now})
            pipe.expire(key, self.seconds)
            results = await pipe.execute()

        cardinality = results[1]
        if cardinality >= self.times:
            raise RateLimitExceeded()
