from typing import Optional
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from datetime import timedelta

from backend_estudiantil.adapters.db.sqlalchemy_user_repository import SQLAlchemyUserRepository
from backend_estudiantil.adapters.security.jwt_authenticator import JWTAuthenticator
from backend_estudiantil.config.settings import settings
from backend_estudiantil.domain.models.user import User
from backend_estudiantil.domain.services.user_service import UserService
from backend_estudiantil.ports.repositories.user_repository import UserRepository
from backend_estudiantil.ports.security.authenticator import Authenticator
from backend_estudiantil.schemas.auth import LoginRequest, Token
from backend_estudiantil.schemas.user import UserCreate, UserRead

class SocialAuthRequest(BaseModel):
    provider: str
    email: EmailStr
    name: Optional[str] = None
    avatar: Optional[str] = None
    telefono: Optional[str] = None
    carrera: Optional[str] = None
    universidad: Optional[str] = None

router = APIRouter(prefix="/auth", tags=["auth"])

def get_user_repository() -> UserRepository:
    return SQLAlchemyUserRepository()

def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)

def get_authenticator() -> Authenticator:
    return JWTAuthenticator()

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, service: UserService = Depends(get_user_service)):
    """Registro de nuevo estudiante o usuario en la plataforma."""
    try:
        user = await service.create_user(payload)
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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest,
    response: Response,
    service: UserService = Depends(get_user_service),
    auth: Authenticator = Depends(get_authenticator),
):
    """Inicio de sesión con validación bcrypt y emisión de JWT + Cookie HttpOnly."""
    repo = service.repo
    user = await repo.get_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    if not service._verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta inactiva o suspendida")

    # Crear tokens incluyendo rol (sub debe ser string según el estándar JWT)
    access_token = auth.create_access_token({"sub": str(user.id), "role": user.rol})
    refresh_token = auth.create_refresh_token({"sub": str(user.id), "role": user.rol})

    # Guardar refresh_token en cookie segura HttpOnly
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        expires_in=float(timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds()),
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(request: Request, auth: Authenticator = Depends(get_authenticator)):
    """Renovación del Access Token a partir de la cookie HttpOnly."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token faltante en cookies")
    try:
        payload = auth.decode_token(refresh_token)
        user_id = payload.get("sub")
        role = payload.get("role", "user")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    access_token = auth.create_access_token({"sub": user_id, "role": role})
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=role,
        expires_in=float(timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds()),
    )

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    """Cierre de sesión: invalida y elimina la cookie de refresh token."""
    response.delete_cookie(
        key="refresh_token",
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    return {"message": "Sesión cerrada correctamente"}

@router.post("/social-login", response_model=Token)
async def social_login(
    payload: SocialAuthRequest,
    response: Response,
    service: UserService = Depends(get_user_service),
    auth: Authenticator = Depends(get_authenticator),
):
    """Autenticación o registro federado con Google, X (Twitter) o Facebook."""
    repo = service.repo
    user = await repo.get_by_email(payload.email)
    if not user:
        user = User(
            correo_institucional=payload.email,
            password_hash="",  # Sin contraseña local requerida para auth federada
            name=payload.name or payload.email.split("@")[0],
            rol="usuario",
            estado_cuenta="activo",
            verificado_comunidad=True,
            telefono=payload.telefono or "",
            programa_area=payload.carrera or "Estudiante Universitario",
            universidad=payload.universidad or "Universidad",
        )
        user = await repo.create(user)
    else:
        if payload.name and (not user.nombre or user.nombre == "Estudiante"):
            user.name = payload.name
            await repo.update(user)

    role = user.rol
    access_token = auth.create_access_token({"sub": str(user.id), "role": role})
    refresh_token = auth.create_refresh_token({"sub": str(user.id), "role": role})

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=role,
        expires_in=float(timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds()),
    )
