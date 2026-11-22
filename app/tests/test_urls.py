import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.short_url import ShortURL


@pytest.mark.asyncio
async def test_create_url_success(client: AsyncClient, auth_headers, db_session):
    payload = {
        "original_url": "https://example.com/some/very/long/path",
        "custom_alias": "myalias",
        "is_active": True,
    }
    response = await client.post("/api/v1/urls", json=payload, headers=auth_headers)
    assert response.status_code == 201

    data = response.json()
    assert data["original_url"] == "https://example.com/some/very/long/path"
    assert data["custom_alias"] == "myalias"
    assert "short_code" in data

    # Verify short URL exists in the database
    res = await db_session.execute(select(ShortURL).where(ShortURL.custom_alias == "myalias"))
    url = res.scalar_one_or_none()
    assert url is not None
    assert url.original_url == "https://example.com/some/very/long/path"


@pytest.mark.asyncio
async def test_create_url_conflict_alias(client: AsyncClient, auth_headers, test_user, db_session):
    # Setup alias first
    url1 = ShortURL(
        original_url="https://google.com",
        short_code="gcode",
        custom_alias="conflictalias",
        owner_id=test_user.id,
    )
    db_session.add(url1)
    await db_session.commit()

    payload = {
        "original_url": "https://yahoo.com",
        "custom_alias": "conflictalias",
    }
    response = await client.post("/api/v1/urls", json=payload, headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "alias_already_exists"


@pytest.mark.asyncio
async def test_list_urls_paginated_and_sorted(client: AsyncClient, auth_headers, test_user, db_session):
    # Seed 3 urls
    for i in range(3):
        url = ShortURL(
            original_url=f"https://site{i}.com",
            short_code=f"code{i}",
            owner_id=test_user.id,
            clicks=i,
        )
        db_session.add(url)
    await db_session.commit()

    response = await client.get("/api/v1/urls?page=1&page_size=2&sort=clicks", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    # Verify descending clicks sorting
    assert data["items"][0]["clicks"] == 2
    assert data["items"][1]["clicks"] == 1


@pytest.mark.asyncio
async def test_get_url_by_id(client: AsyncClient, auth_headers, test_user, db_session):
    url = ShortURL(
        original_url="https://mytest.com",
        short_code="testcode",
        owner_id=test_user.id,
    )
    db_session.add(url)
    await db_session.commit()
    await db_session.refresh(url)

    response = await client.get(f"/api/v1/urls/{url.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["short_code"] == "testcode"


@pytest.mark.asyncio
async def test_update_url(client: AsyncClient, auth_headers, test_user, db_session):
    url = ShortURL(
        original_url="https://mytest.com",
        short_code="testcode",
        owner_id=test_user.id,
    )
    db_session.add(url)
    await db_session.commit()
    await db_session.refresh(url)

    payload = {
        "original_url": "https://updatedtest.com",
        "custom_alias": "newalias",
    }
    response = await client.put(f"/api/v1/urls/{url.id}", json=payload, headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["original_url"] == "https://updatedtest.com"
    assert data["custom_alias"] == "newalias"


@pytest.mark.asyncio
async def test_delete_url_soft_delete(client: AsyncClient, auth_headers, test_user, db_session):
    url = ShortURL(
        original_url="https://mytest.com",
        short_code="testcode",
        owner_id=test_user.id,
        is_active=True,
    )
    db_session.add(url)
    await db_session.commit()
    await db_session.refresh(url)

    response = await client.delete(f"/api/v1/urls/{url.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify is_active is now False in DB
    await db_session.refresh(url)
    assert url.is_active is False


@pytest.mark.asyncio
async def test_popular_urls_are_scoped_to_authenticated_owner(
    client: AsyncClient, auth_headers, test_user, db_session
):
    from app.core.security import hash_password
    from app.models.user import User

    own_url = ShortURL(
        original_url="https://my-owned-site.example",
        short_code="myowned",
        owner_id=test_user.id,
        clicks=3,
    )
    other_user = User(
        username="another_user",
        email="another_user@example.com",
        password_hash=hash_password("Password123!"),
    )
    db_session.add(other_user)
    await db_session.flush()
    other_url = ShortURL(
        original_url="https://another-users-private-destination.example",
        short_code="notmine",
        owner_id=other_user.id,
        clicks=1000,
    )
    db_session.add_all([own_url, other_url])
    await db_session.commit()

    response = await client.get("/api/v1/urls/popular?limit=10", headers=auth_headers)

    assert response.status_code == 200
    returned_codes = {item["short_code"] for item in response.json()}
    assert returned_codes == {"myowned"}


@pytest.mark.asyncio
async def test_create_url_rejects_non_http_destination(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/urls",
        json={"original_url": "ftp://files.example.com/archive.zip"},
        headers=auth_headers,
    )
    assert response.status_code == 422
