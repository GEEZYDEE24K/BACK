import pytest
import respx
import httpx
from fastapi.testclient import TestClient
from backend_estudiantil.infrastructure.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_db(monkeypatch):
    # Resetear la base de datos de pruebas si es necesario
    yield

def test_login_and_refresh():
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "user"
    refresh_response = client.post("/auth/refresh", cookies={"refresh_token": response.cookies.get("refresh_token")})
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert refresh_data["access_token"] != data["access_token"]
    assert refresh_data["role"] == "user"

@respx.mock
@pytest.mark.asyncio
async def test_google_oauth_flow(monkeypatch):
    token_url = "https://oauth2.googleapis.com/token"
    respx.post(token_url).mock(return_value=httpx.Response(200, json={"access_token": "mock_access_token"}))
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    respx.get(userinfo_url).mock(return_value=httpx.Response(200, json={"email": "googleuser@example.com", "name": "Google User"}))
    async with httpx.AsyncClient(app=app, base_url="http://testserver") as async_client:
        response = await async_client.get("/auth/google/callback", params={"code": "dummy_code"})
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "user"
    assert "access_token" in data
    assert "refresh_token" in response.cookies
