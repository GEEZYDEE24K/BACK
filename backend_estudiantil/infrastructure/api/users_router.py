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
