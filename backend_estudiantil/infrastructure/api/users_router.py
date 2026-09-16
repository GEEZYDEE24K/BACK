from fastapi import APIRouter, Depends, HTTPException, status

from backend_estudiantil.adapters.db.sqlalchemy_user_repository import SQLAlchemyUserRepository
from backend_estudiantil.domain.services.user_service import UserService
from backend_estudiantil.schemas.user import UserCreate, UserRead, UserUpdate
from backend_estudiantil.ports.repositories.user_repository import UserRepository

from backend_estudiantil.infrastructure.security import get_current_user

router = APIRouter(prefix="/usuarios", tags=["users"])

def get_user_repository() -> UserRepository:
    return SQLAlchemyUserRepository()

def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user)
):
    # Only admin can create users via this route; registration uses /auth/register
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    user = await service.create_user(payload)
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )

@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user)
):
    # Any authenticated user can view any user
    user = await service.get_user(user_id)
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )

@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user)
):
    # Users can update themselves; admin can update any
    if current_user["id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    user = await service.update_user(user_id, payload)
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user)
):
    # Only admin can delete users
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    await service.delete_user(user_id)
    return None
