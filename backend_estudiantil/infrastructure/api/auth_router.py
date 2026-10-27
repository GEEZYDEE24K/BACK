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

from fastapi.responses import HTMLResponse

class SocialAuthRequest(BaseModel):
    provider: str
    email: EmailStr
    name: Optional[str] = None
    avatar: Optional[str] = None
    telefono: Optional[str] = None
    carrera: Optional[str] = None
    universidad: Optional[str] = None

class ConfirmarCodigoRequest(BaseModel):
    email: EmailStr
    codigo: str

class ReenviarCodigoRequest(BaseModel):
    email: EmailStr

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
            semestre=user.semestre,
            foto_url=user.foto_url,
            perfil_completo=user.perfil_completo,
            verificado_comunidad=user.verificado_comunidad,
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
        role=user.rol,
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
        es_inst = settings.es_dominio_institucional(payload.email)
        universidad = settings.obtener_universidad_por_dominio(payload.email) if es_inst else (payload.universidad or "Universidad")
        user = User(
            correo_institucional=payload.email,
            password_hash="",  # Sin contraseña local requerida para auth federada
            name=payload.name or payload.email.split("@")[0],
            rol="usuario",
            estado_cuenta="activo",
            verificado_comunidad=es_inst,
            telefono=payload.telefono or "",
            programa_area=payload.carrera or "Estudiante Universitario",
            universidad=universidad,
            perfil_completo=bool(payload.name and universidad and payload.carrera),
        )
        user = await repo.create(user)
    else:
        if payload.name and (not user.name or user.name == "Estudiante"):
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

@router.post("/confirmar-codigo")
async def confirmar_codigo(
    payload: ConfirmarCodigoRequest,
    service: UserService = Depends(get_user_service),
):
    """Confirma el código de 6 dígitos enviado al correo institucional para activar la verificación de comunidad."""
    try:
        user = await service.confirmar_codigo_verificacion(payload.email, payload.codigo)
        return {
            "message": "Correo institucional verificado exitosamente",
            "verificado_comunidad": user.verificado_comunidad,
            "universidad": user.universidad,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/confirmar-correo", response_class=HTMLResponse)
async def confirmar_correo(
    email: str,
    codigo: str,
    service: UserService = Depends(get_user_service),
):
    """Enlace directo de confirmación para el correo institucional."""
    try:
        user = await service.confirmar_codigo_verificacion(email, codigo)
        es_usbmed = "usbmed.edu.co" in (email or "").lower() or "buenaventura" in (user.universidad or "").lower()
        titulo = "🎓 ¡Felicitaciones Bonaventuriano!" if es_usbmed else "✓ ¡Correo Verificado!"
        desc_univ = "Universidad de San Buenaventura Medellín (USBMED)" if es_usbmed else (user.universidad or "tu universidad")
        badge_text = "Estudiante USBMED Verificado" if es_usbmed else "Estudiante Verificado"
        btn_color = "#ea580c" if es_usbmed else "#4f46e5"

        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Correo Verificado - SwapU</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #0c0a09; color: #fafaf9; }}
                .card {{ background: #1c1917; padding: 2.5rem; border-radius: 14px; border: 1px solid #44403c; text-align: center; max-width: 480px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }}
                h1 {{ color: {btn_color}; margin-top: 0; font-size: 1.6rem; }}
                p {{ color: #a8a29e; line-height: 1.6; font-size: 0.95rem; }}
                .badge {{ display: inline-block; background: rgba(234, 88, 12, 0.2); color: #fb923c; border: 1px solid rgba(251, 146, 60, 0.4); padding: 0.35rem 0.85rem; border-radius: 999px; font-weight: 700; font-size: 0.85rem; margin: 0.5rem 0 1rem 0; }}
                .btn {{ display: inline-block; margin-top: 1.5rem; padding: 0.85rem 1.8rem; background: {btn_color}; color: white; text-decoration: none; border-radius: 8px; font-weight: 700; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>{titulo}</h1>
                <div class="badge">🏷 {badge_text}</div>
                <p>Tu correo institucional <strong>{email}</strong> ha sido confirmado con éxito. Tu cuenta ahora cuenta con el distintivo oficial de <strong>{badge_text}</strong> en {desc_univ}.</p>
                <p style="font-size: 0.85rem; color: #78716c;">Tienes acceso preferencial a matches académicos y entregas comunitarias en campus.</p>
                <a href="/" class="btn">Ingresar a SwapU</a>
            </div>
        </body>
        </html>
        """
    except ValueError as e:
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Error de Verificación - SwapU</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f8fafc; }}
                .card {{ background: white; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); text-align: center; max-width: 450px; }}
                h1 {{ color: #dc2626; margin-top: 0; }}
                p {{ color: #475569; line-height: 1.5; }}
                .btn {{ display: inline-block; margin-top: 1.5rem; padding: 0.75rem 1.5rem; background: #4f46e5; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>⚠ No se pudo verificar</h1>
                <p>{str(e)}</p>
                <a href="/" class="btn">Volver a SwapU</a>
            </div>
        </body>
        </html>
        """

@router.post("/reenviar-codigo")
async def reenviar_codigo(
    payload: ReenviarCodigoRequest,
    service: UserService = Depends(get_user_service),
):
    """Reenvía un nuevo código de confirmación al correo institucional."""
    try:
        await service.reenviar_codigo_verificacion(payload.email)
        return {"message": "Código de confirmación reenviado exitosamente"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

