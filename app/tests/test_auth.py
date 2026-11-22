import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.user import User
from app.database.redis import redis_client


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient, db_session):
    payload = {
        "username": "new_user",
        "email": "new_user@example.com",
        "password": "Password123!",
    }
    response = await client.post("/api/v1/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["username"] == "new_user"
    assert data["email"] == "new_user@example.com"
    assert "id" in data

    # Verify user exists in the database
    res = await db_session.execute(select(User).where(User.username == "new_user"))
    user = res.scalar_one_or_none()
    assert user is not None
    assert user.email == "new_user@example.com"


@pytest.mark.asyncio
async def test_register_user_duplicate(client: AsyncClient, test_user):
    payload = {
        "username": test_user.username,
        "email": "different_email@example.com",
        "password": "Password123!",
    }
    response = await client.post("/api/v1/register", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "user_already_exists"


@pytest.mark.asyncio
async def test_register_user_weak_password(client: AsyncClient):
    payload = {
        "username": "weak_pw_user",
        "email": "weak@example.com",
        "password": "simplepassword",  # lacks caps, numbers, special characters
    }
    response = await client.post("/api/v1/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    payload = {
        "email": test_user.email,
        "password": "Password123!",
    }
    response = await client.post("/api/v1/login", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == test_user.username


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_user):
    payload = {
        "email": test_user.email,
        "password": "WrongPassword!",
    }
    response = await client.post("/api/v1/login", json=payload)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, auth_headers):
    # Verify auth endpoint is protected
    response = await client.post("/api/v1/logout")
    assert response.status_code == 401

    # Logout request with auth headers
    response = await client.post("/api/v1/logout", headers=auth_headers)
    assert response.status_code == 200
    assert "logged out successfully" in response.json()["message"]

    # Verify request with the same headers is now rejected (blacklisted)
    response = await client.post("/api/v1/logout", headers=auth_headers)
    assert response.status_code == 401
    assert "logged out" in response.json()["error"]["message"]
