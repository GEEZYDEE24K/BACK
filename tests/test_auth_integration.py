import pytest
import pytest_asyncio
import respx
import httpx
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from backend_estudiantil.infrastructure.main import app
from backend_estudiantil.config.settings import settings
from backend_estudiantil.adapters.db import Base, get_engine

@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    """Inicializa la base de datos de pruebas SQLite aislada para cada test."""
    original_url = settings.DATABASE_URL
    test_db_url = "sqlite+aiosqlite:///./test_auth.db"
    settings.DATABASE_URL = test_db_url
    engine = get_engine(test_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    settings.DATABASE_URL = original_url
    get_engine(original_url)

def test_health_and_database_connection():
    """Verifica que la API y la conexión a la base de datos respondan correctamente."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        db_response = client.get("/health/db")
        assert db_response.status_code == 200
        assert db_response.json()["database"]["status"] == "conectado"

def test_login_and_refresh():
    with TestClient(app, cookies={}) as client:
        # 1. Registrar primero al usuario para que exista en BD
        reg_resp = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password123", "name": "Test User", "role": "user"},
        )
        assert reg_resp.status_code == 201

        # 2. Login
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        # El rol puede ser 'usuario' o 'user' según configuración
        assert data["role"] in ("user", "usuario")

        # Extraer cookie del header Set-Cookie directamente
        refresh_token_value = None
        for cookie in response.headers.get_list("set-cookie"):
            if "refresh_token" in cookie:
                refresh_token_value = cookie.split("=", 1)[1].split(";")[0]
                break

        # 3. Refresh token
        if refresh_token_value:
            refresh_response = client.post(
                "/auth/refresh",
                cookies={"refresh_token": refresh_token_value},
            )
            assert refresh_response.status_code == 200
            refresh_data = refresh_response.json()
            assert "access_token" in refresh_data
            assert refresh_data["role"] in ("user", "usuario")

        # 4. Logout (limpia la cookie)
        logout_resp = client.post("/auth/logout")
        assert logout_resp.status_code == 200

@respx.mock
@pytest.mark.asyncio
async def test_google_oauth_flow():
    token_url = "https://oauth2.googleapis.com/token"
    respx.post(token_url).mock(return_value=httpx.Response(200, json={"access_token": "mock_access_token"}))
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    respx.get(userinfo_url).mock(return_value=httpx.Response(200, json={"email": "googleuser@example.com", "name": "Google User"}))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        response = await async_client.get("/auth/google/callback", params={"code": "dummy_code"})
    assert response.status_code == 200
    data = response.json()
    assert data["role"] in ("user", "usuario")
    assert "access_token" in data
    assert "refresh_token" in response.cookies
