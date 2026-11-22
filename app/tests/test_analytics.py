import pytest
from httpx import AsyncClient
from app.models.short_url import ShortURL
from app.models.click_analytics import ClickAnalytics

@pytest.mark.asyncio
async def test_get_url_analytics_success(client: AsyncClient, auth_headers, test_user, db_session):
    url = ShortURL(original_url="https://analytics-test.com", short_code="anacode", owner_id=test_user.id, clicks=2)
    db_session.add(url)
    await db_session.commit()
    await db_session.refresh(url)
    db_session.add_all([
        ClickAnalytics(url_id=url.id, ip="192.168.1.1", browser="Firefox", device="Mobile", os="Android", referrer="https://twitter.com", country="US"),
        ClickAnalytics(url_id=url.id, ip="192.168.1.2", browser="Firefox", device="Desktop", os="macOS", referrer="https://linkedin.com", country="US"),
    ])
    await db_session.commit()
    response = await client.get(f"/api/v1/analytics/{url.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["url_id"] == url.id
    assert data["short_code"] == "anacode"
    assert data["total_clicks"] == 2
    assert data["stored_click_events"] == 2
    assert data["browsers"] == [{"name": "Firefox", "count": 2}]
    assert len(data["devices"]) == 2
    assert len(data["recent_clicks"]) == 2

@pytest.mark.asyncio
async def test_get_url_analytics_unauthorized_owner(client: AsyncClient, test_user, db_session):
    url = ShortURL(original_url="https://private.com", short_code="private", owner_id=test_user.id)
    db_session.add(url)
    await db_session.commit()
    response = await client.get(f"/api/v1/analytics/{url.id}")
    assert response.status_code == 401
    from app.models.user import User
    from app.core.security import hash_password, create_access_token
    other_user = User(username="other_user", email="other@example.com", password_hash=hash_password("Password123!"))
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    token, _, _ = create_access_token(str(other_user.id))
    response = await client.get(f"/api/v1/analytics/{url.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "url_not_found"
