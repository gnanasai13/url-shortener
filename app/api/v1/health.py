from fastapi import APIRouter, status
from sqlalchemy import text

from app.database.redis import redis_client
from app.database.session import async_session_factory

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> dict[str, str]:
    async with async_session_factory() as session:
        await session.execute(text("SELECT 1"))

    await redis_client.ping()
    return {"database": "ok", "redis": "ok"}
