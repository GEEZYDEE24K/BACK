import pytest
import io
import uuid
from httpx import AsyncClient, ASGITransport
from backend_estudiantil.infrastructure.main import app
from backend_estudiantil.adapters.db import get_session_factory, UserORM
from backend_estudiantil.adapters.security.jwt_authenticator import JWTAuthenticator
from sqlalchemy import select


@pytest.fixture
def jwt_auth():
    return JWTAuthenticator()


@pytest.mark.asyncio
async def test_verificacion_comunidad_por_dominio_institucional(jwt_auth):
    """Verifica que un correo de dominio institucional active verificado_comunidad=True automáticamente."""
    transport = ASGITransport(app=app)
    uid = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Usuario con dominio institucional (@unal.edu.co)
        res_inst = await ac.post("/auth/register", json={
            "email": f"estudiante_{uid}@unal.edu.co",
            "password": "Password123*",
            "name": "Carlos Rodríguez",
            "carrera": "Ingeniería de Sistemas",
        })
        assert res_inst.status_code == 201
        data_inst = res_inst.json()
        assert data_inst["verificado_comunidad"] is True
        assert "Universidad Nacional" in (data_inst.get("universidad") or "")

        # 2. Usuario con correo externo (@gmail.com)
        res_ext = await ac.post("/auth/register", json={
            "email": f"usuario_ext_{uid}@gmail.com",
            "password": "Password123*",
            "name": "Pedro Gómez",
        })
        assert res_ext.status_code == 201
        data_ext = res_ext.json()
        assert data_ext["verificado_comunidad"] is False


@pytest.mark.asyncio
async def test_cuenta_general_puede_publicar_y_bloqueado_es_rechazado(jwt_auth):
    """Verifica que una cuenta general/Gmail pueda publicar y proponer trueques, y que una cuenta bloqueada sea rechazada."""
    transport = ASGITransport(app=app)
    uid = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Registrar usuario externo general (Gmail)
        email = f"general_{uid}@gmail.com"
        await ac.post("/auth/register", json={
            "email": email,
            "password": "Password123*",
            "name": "Usuario General",
        })

        login_res = await ac.post("/auth/login", json={
            "email": email,
            "password": "Password123*",
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Usuario general puede publicar exitosamente
        pub_res = await ac.post("/publicaciones/", json={
            "titulo": "Libro de Lectura General",
            "autor": "Autor Ejemplo",
            "categoria_id": 1,
        }, headers=headers)
        assert pub_res.status_code == 201

        # Si la cuenta pasa a estado 'bloqueado', no puede publicar
        factory = get_session_factory()
        async with factory() as session:
            q = await session.execute(select(UserORM).where(UserORM.correo_institucional == email))
            u = q.scalar_one()
            u.estado_cuenta = "bloqueado"
            await session.commit()

        pub_bloq = await ac.post("/publicaciones/", json={
            "titulo": "Otro Libro",
            "autor": "Autor",
            "categoria_id": 1,
        }, headers=headers)
        assert pub_bloq.status_code == 403
        assert any(m in pub_bloq.json()["detail"] for m in ["Inactive", "bloqueada"])


@pytest.mark.asyncio
async def test_flujo_solicitud_y_aprobacion_carne_estudiantil(jwt_auth):
    """Flujo completo de carga de carné, privacidad y aprobación por moderador."""
    transport = ASGITransport(app=app)
    uid = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Registrar usuario externo no verificado
        alumno_email = f"alumno_{uid}@hotmail.com"
        reg_alumno = await ac.post("/auth/register", json={
            "email": alumno_email,
            "password": "Password123*",
            "name": "Juan Alumno",
            "carrera": "Derecho",
            "universidad": "Universidad Libre",
        })
        alumno_id = reg_alumno.json()["id"]

        login_alumno = await ac.post("/auth/login", json={"email": alumno_email, "password": "Password123*"})
        alumno_token = login_alumno.json()["access_token"]
        alumno_headers = {"Authorization": f"Bearer {alumno_token}"}

        # 2. Registrar moderador
        mod_email = f"mod_{uid}@unal.edu.co"
        await ac.post("/auth/register", json={
            "email": mod_email,
            "password": "Password123*",
            "name": "Mod Staff",
        })
        # Promover a moderador
        factory = get_session_factory()
        async with factory() as session:
            q = await session.execute(select(UserORM).where(UserORM.correo_institucional == mod_email))
            mod_user = q.scalar_one()
            mod_user.rol = "moderador"
            await session.commit()

        login_mod = await ac.post("/auth/login", json={"email": mod_email, "password": "Password123*"})
        mod_token = login_mod.json()["access_token"]
        mod_headers = {"Authorization": f"Bearer {mod_token}"}

        # 3. Alumno sube carné
        fake_image = io.BytesIO(b"FAKE_CARNET_IMAGE_BYTES_12345")
        files = {"carnet": ("mi_carnet.jpg", fake_image, "image/jpeg")}
        upload_res = await ac.post("/usuarios/me/solicitar-verificacion", files=files, headers=alumno_headers)
        assert upload_res.status_code == 200
        assert "Carné recibido" in upload_res.json()["msg"]

        # 4. Privacidad: Otro usuario común intenta ver el carné de este alumno -> 403 Forbidden
        otro_email = f"curioso_{uid}@gmail.com"
        await ac.post("/auth/register", json={"email": otro_email, "password": "Password123*", "name": "Curioso"})
        login_otro = await ac.post("/auth/login", json={"email": otro_email, "password": "Password123*"})
        otro_headers = {"Authorization": f"Bearer {login_otro.json()['access_token']}"}

        priv_res = await ac.get(f"/usuarios/{alumno_id}/carnet", headers=otro_headers)
        assert priv_res.status_code == 403

        # 5. El moderador lista pendientes
        pendientes_res = await ac.get("/usuarios/verificaciones/pendientes", headers=mod_headers)
        assert pendientes_res.status_code == 200
        ids_pendientes = [u["id"] for u in pendientes_res.json()]
        assert str(alumno_id) in ids_pendientes

        # 6. El moderador aprueba la verificación
        aprobar_res = await ac.post(f"/usuarios/{alumno_id}/verificar", headers=mod_headers)
        assert aprobar_res.status_code == 200
        assert aprobar_res.json()["verificado_comunidad"] is True
