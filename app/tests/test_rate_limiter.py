import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, Depends
from app.dependencies.rate_limiter import RateLimiter
from app.database.redis import redis_client
from app.core.exceptions import AppException, app_exception_handler

@pytest.fixture(autouse=True)
async def clear_redis():
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match="rate_limit:test_limit:*")
        if keys:
            await redis_client.delete(*keys)
        if cursor == 0:
            break
    yield
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match="rate_limit:test_limit:*")
        if keys:
            await redis_client.delete(*keys)
        if cursor == 0:
            break

@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit():
    app = FastAPI()
    app.add_exception_handler(AppException, app_exception_handler)
    @app.get("/test-limit", dependencies=[Depends(RateLimiter(times=3, seconds=5, key_prefix="test_limit"))])
    async def test_limit_route():
        return {"status": "ok"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for _ in range(3):
            response = await ac.get("/test-limit")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit():
    app = FastAPI()
    app.add_exception_handler(AppException, app_exception_handler)
    @app.get("/test-limit", dependencies=[Depends(RateLimiter(times=3, seconds=5, key_prefix="test_limit"))])
    async def test_limit_route():
        return {"status": "ok"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for _ in range(3):
            assert (await ac.get("/test-limit")).status_code == 200
        response = await ac.get("/test-limit")
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "rate_limit_exceeded"

@pytest.mark.asyncio
async def test_rate_limiter_resets_after_window():
    app = FastAPI()
    app.add_exception_handler(AppException, app_exception_handler)
    @app.get("/test-limit", dependencies=[Depends(RateLimiter(times=2, seconds=2, key_prefix="test_limit"))])
    async def test_limit_route():
        return {"status": "ok"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        assert (await ac.get("/test-limit")).status_code == 200
        assert (await ac.get("/test-limit")).status_code == 200
        assert (await ac.get("/test-limit")).status_code == 429
        await asyncio.sleep(2.1)
        assert (await ac.get("/test-limit")).status_code == 200
