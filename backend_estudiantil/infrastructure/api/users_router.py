from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend_estudiantil.adapters.db.sqlalchemy_user_repository import SQLAlchemyUserRepository
from backend_estudiantil.domain.services.user_service import UserService
from backend_estudiantil.schemas.user import UserCreate, UserRead, UserUpdate
from backend_estudiantil.ports.repositories.user_repository import UserRepository
from backend_estudiantil.infrastructure.security import get_current_user

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

def get_user_repository() -> UserRepository:
    return SQLAlchemyUserRepository()

def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)

def _user_to_read(user) -> UserRead:
    return UserRead(
        id=str(user.id),
        email=user.correo_institucional,
        name=user.name,
        role=user.rol,
        is_active=user.is_active,
        telefono=user.telefono,
        carrera=user.programa_area,
        universidad=user.universidad,
        semestre=getattr(user, "semestre", None),
        foto_url=getattr(user, "foto_url", None),
        verificado_comunidad=getattr(user, "verificado_comunidad", False),
        perfil_completo=getattr(user, "perfil_completo", False),
        created_at=user.fecha_registro.isoformat() if hasattr(user.fecha_registro, "isoformat") else str(user.fecha_registro),
        updated_at=user.fecha_registro.isoformat() if hasattr(user.fecha_registro, "isoformat") else str(user.fecha_registro),
    )

# ------------------------------------------------------------------------------
# ENDPOINTS DE PERFIL DEL ESTUDIANTE / USUARIO ACTUAL (/usuarios/me)
# ------------------------------------------------------------------------------
@router.get("/me", response_model=UserRead)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Consulta el perfil del usuario/estudiante autenticado."""
    try:
        user = await service.get_user(current_user["id"])
        return _user_to_read(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/me", response_model=UserRead)
async def update_my_profile(
    payload: UserUpdate,
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Actualiza la información del perfil del estudiante autenticado."""
    try:
        user = await service.update_user(current_user["id"], payload)
        return _user_to_read(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# ------------------------------------------------------------------------------
# CRUD GENERAL DE USUARIOS
# ------------------------------------------------------------------------------
@router.get("/", response_model=List[UserRead])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user),
):
    """Listado paginado de usuarios (requiere autenticación)."""
    users = await service.get_users(skip=skip, limit=limit)
    return [_user_to_read(u) for u in users]

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user),
):
    """Creación administrativa de usuarios (solo admin)."""
    if current_user.get("role") not in ("admin", "administrador"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
    try:
        user = await service.create_user(payload)
        return _user_to_read(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user),
):
    """Obtiene el detalle de un usuario por su ID."""
    try:
        user = await service.get_user(user_id)
        return _user_to_read(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user),
):
    """Actualiza la información de un usuario (propio o por admin)."""
    if current_user["id"] != user_id and current_user.get("role") not in ("admin", "administrador"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
    try:
        user = await service.update_user(user_id, payload)
        return _user_to_read(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user),
):
    """Eliminación de usuario (solo admin)."""
    if current_user.get("role") not in ("admin", "administrador"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
    try:
        await service.delete_user(user_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ------------------------------------------------------------------------------
# VERIFICACIÓN MANUAL DE COMUNIDAD (CARNÉ ESTUDIANTIL)
# ------------------------------------------------------------------------------
import os
import uuid
from pathlib import Path
from fastapi import File, UploadFile
from fastapi.responses import FileResponse
from backend_estudiantil.adapters.db import AuditoriaLogORM, get_session_factory

CARNET_STORAGE_DIR = Path("./storage/carnets")


@router.post("/me/solicitar-verificacion", summary="Subir carné para solicitar verificación manual")
async def solicitar_verificacion_comunidad(
    carnet: UploadFile = File(..., description="Foto del carné estudiantil o documento universitario"),
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Permite al estudiante subir su carné para ser verificado manualmente por un moderador."""
    user = await service.get_user(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    CARNET_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(carnet.filename or "carnet.jpg").suffix or ".jpg"
    filename = f"carnet_{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    dest_path = CARNET_STORAGE_DIR / filename

    content = await carnet.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El archivo excede el tamaño máximo permitido (10 MB)")

    with open(dest_path, "wb") as f:
        f.write(content)

    user.carnet_path = str(dest_path).replace("\\", "/")
    await service.repo.update(user)

    # Registrar evento de auditoría
    factory = get_session_factory()
    async with factory() as session:
        audit = AuditoriaLogORM(
            usuario_id=user.id,
            usuario_email=user.correo_institucional,
            usuario_rol=user.rol,
            ip_origen="127.0.0.1",
            accion="SOLICITUD_VERIFICACION_CARNET",
            recurso="usuario:carnet",
            metodo_http="POST",
            endpoint="/usuarios/me/solicitar-verificacion",
            estado_http=200,
            exito=True,
            detalle="El estudiante ha cargado su carné estudiantil para revisión de moderación",
        )
        session.add(audit)
        await session.commit()

    return {
        "msg": "Carné recibido exitosamente. Tu solicitud está en cola de revisión por el equipo de moderación.",
        "verificado_comunidad": user.verificado_comunidad,
    }


@router.get("/{user_id}/carnet", summary="Ver carné estudiantil (Solo moderador, admin o titular)")
async def obtener_carnet(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Consulta privada del carné estudiantil. Solo moderador, admin o el propio usuario."""
    es_titular = str(current_user["id"]) == str(user_id)
    es_staff = current_user.get("role") in ("admin", "administrador", "moderador")

    if not (es_titular or es_staff):
        raise HTTPException(status_code=403, detail="Acceso denegado: el carné estudiantil es información privada")

    user = await service.get_user(user_id)
    if not user or not user.carnet_path or not os.path.exists(user.carnet_path):
        raise HTTPException(status_code=404, detail="El usuario no tiene un carné registrado o no está disponible")

    return FileResponse(user.carnet_path)


@router.get("/verificaciones/pendientes", response_model=List[UserRead], summary="Listar solicitudes pendientes de carné")
async def listar_verificaciones_pendientes(
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Lista usuarios que tienen carné cargado y aún no han sido verificados (moderadores y administradores)."""
    if current_user.get("role") not in ("admin", "administrador", "moderador"):
        raise HTTPException(status_code=403, detail="Permisos insuficientes de moderación")

    users = await service.get_users(skip=0, limit=100)
    pendientes = [u for u in users if getattr(u, "carnet_path", None) and not u.verificado_comunidad]
    return [_user_to_read(u) for u in pendientes]


@router.post("/{user_id}/verificar", response_model=UserRead, summary="Aprobar verificación de comunidad")
async def aprobar_verificacion(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Aprueba la verificación de comunidad de un usuario tras revisar su carné."""
    if current_user.get("role") not in ("admin", "administrador", "moderador"):
        raise HTTPException(status_code=403, detail="Permisos insuficientes de moderación")

    user = await service.get_user(user_id)
    user.verificado_comunidad = True
    actualizado = await service.repo.update(user)

    # Registrar en auditoría
    factory = get_session_factory()
    async with factory() as session:
        audit = AuditoriaLogORM(
            usuario_id=int(current_user["id"]) if str(current_user.get("id")).isdigit() else None,
            usuario_email=current_user.get("email"),
            usuario_rol=current_user.get("role"),
            ip_origen="127.0.0.1",
            accion="VERIFICACION_COMUNIDAD_APROBADA",
            recurso=f"usuario:{user_id}",
            metodo_http="POST",
            endpoint=f"/usuarios/{user_id}/verificar",
            estado_http=200,
            exito=True,
            detalle=f"Verificación de comunidad aprobada manualmente por {current_user.get('role')}",
        )
        session.add(audit)
        await session.commit()

    return _user_to_read(actualizado)


@router.post("/{user_id}/rechazar-verificacion", response_model=UserRead, summary="Rechazar verificación de carné")
async def rechazar_verificacion(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Rechaza la verificación de carné de un estudiante."""
    if current_user.get("role") not in ("admin", "administrador", "moderador"):
        raise HTTPException(status_code=403, detail="Permisos insuficientes de moderación")

    user = await service.get_user(user_id)
    user.verificado_comunidad = False
    actualizado = await service.repo.update(user)

    factory = get_session_factory()
    async with factory() as session:
        audit = AuditoriaLogORM(
            usuario_id=int(current_user["id"]) if str(current_user.get("id")).isdigit() else None,
            usuario_email=current_user.get("email"),
            usuario_rol=current_user.get("role"),
            ip_origen="127.0.0.1",
            accion="VERIFICACION_COMUNIDAD_RECHAZADA",
            recurso=f"usuario:{user_id}",
            metodo_http="POST",
            endpoint=f"/usuarios/{user_id}/rechazar-verificacion",
            estado_http=200,
            exito=True,
            detalle=f"Verificación de comunidad rechazada por {current_user.get('role')}",
        )
        session.add(audit)
        await session.commit()

    return _user_to_read(actualizado)
