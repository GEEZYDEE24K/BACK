from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from datetime import timedelta

from backend_estudiantil.adapters.db.sqlalchemy_user_repository import SQLAlchemyUserRepository
from backend_estudiantil.adapters.security.jwt_authenticator import JWTAuthenticator
from backend_estudiantil.domain.services.user_service import UserService
from backend_estudiantil.ports.repositories.user_repository import UserRepository
from backend_estudiantil.ports.security.authenticator import Authenticator
from backend_estudiantil.schemas.auth import LoginRequest, Token
from backend_estudiantil.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

def get_user_repository() -> UserRepository:
    return SQLAlchemyUserRepository()

def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)

def get_authenticator() -> Authenticator:
    return JWTAuthenticator()

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, service: UserService = Depends(get_user_service)):
    try:
        user = await service.create_user(payload)
        return UserRead(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, service: UserService = Depends(get_user_service), auth: Authenticator = Depends(get_authenticator)):
    # Fetch user by email
    repo = service.repo
    user = await repo.get_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Verify password (same hash method as service)
    hashed_input = service._hash_password(payload.password)
    if hashed_input != user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Create tokens including role
    access_token = auth.create_access_token({"sub": user.id, "role": user.role})
    refresh_token = auth.create_refresh_token({"sub": user.id, "role": user.role})
    # Set refresh token as HttpOnly cookie
    response = Response()
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=timedelta(days=7).total_seconds(),
    )
    # Return token response including role
    token_response = Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        expires_in=timedelta(minutes=30).total_seconds(),
    )
    response.body = token_response.json().encode()
    response.media_type = "application/json"
    return response

@router.post("/refresh", response_model=Token)
async def refresh_token(response: Response, request: Request, auth: Authenticator = Depends(get_authenticator)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    try:
        payload = auth.decode_token(refresh_token)
        user_id = payload.get("sub")
        role = payload.get("role", "user")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    # Create new access token including role
    access_token = auth.create_access_token({"sub": user_id, "role": role})
    # Return new access token with role (keep same refresh cookie)
    return Token(access_token=access_token, token_type="bearer", role=role, expires_in=timedelta(minutes=30).total_seconds())
