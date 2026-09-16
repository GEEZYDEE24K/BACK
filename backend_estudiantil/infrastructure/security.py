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

async def get_current_user(token: str = Depends(oauth2_scheme),
                           repo: UserRepository = Depends(get_user_repository),
                           authenticator = Depends(get_authenticator)) -> Optional[dict]:
    try:
        payload = authenticator.decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        user = await repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return {"id": user.id, "email": user.email, "role": payload.get("role", "user"), "name": user.name}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
