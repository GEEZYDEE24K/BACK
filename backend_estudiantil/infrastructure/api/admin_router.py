from fastapi import APIRouter, Depends, HTTPException, status
from backend_estudiantil.adapters.db.sqlalchemy_user_repository import SQLAlchemyUserRepository
from backend_estudiantil.domain.services.user_service import UserService
from backend_estudiantil.ports.repositories.user_repository import UserRepository
from backend_estudiantil.infrastructure.security import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

def get_user_repository() -> UserRepository:
    return SQLAlchemyUserRepository()

def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)

@router.post("/users/{user_id}/promote", status_code=status.HTTP_200_OK)
async def promote_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user),
):
    """Promote a user to the *moderador* role.
    Only an *admin* can perform this action.
    """
    if current_user.get("role") not in ("admin", "administrador"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    # Promote using service method
    promoted_user = await service.promote_to_moderator(user_id)
    return {"msg": f"Usuario {user_id} promovido a {promoted_user.rol}"}
