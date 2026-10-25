from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

from backend_estudiantil.adapters.security.jwt_authenticator import JWTAuthenticator
from backend_estudiantil.ports.repositories.user_repository import UserRepository
from backend_estudiantil.adapters.db.sqlalchemy_user_repository import SQLAlchemyUserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_user_repository() -> UserRepository:
    return SQLAlchemyUserRepository()

def get_authenticator() -> JWTAuthenticator:
    return JWTAuthenticator()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    repo: UserRepository = Depends(get_user_repository),
    authenticator: JWTAuthenticator = Depends(get_authenticator),
) -> dict:
    """Extrae y valida el usuario actual a partir del token JWT de autorización."""
    try:
        payload = authenticator.decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        user = await repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")
        return {
            "id": user.id,
            "email": user.correo_institucional,
            "role": user.rol or payload.get("role", "usuario"),
            "name": user.name,
            "is_active": user.is_active,
            "telefono": user.telefono,
            "carrera": user.programa_area,
            "universidad": user.universidad,
            "created_at": user.fecha_registro.isoformat() if hasattr(user.fecha_registro, "isoformat") else str(user.fecha_registro),
            "updated_at": user.fecha_registro.isoformat() if hasattr(user.fecha_registro, "isoformat") else str(user.fecha_registro),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
