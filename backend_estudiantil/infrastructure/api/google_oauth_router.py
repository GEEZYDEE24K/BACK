from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend_estudiantil.adapters.db.sqlalchemy_user_repository import SQLAlchemyUserRepository
from backend_estudiantil.adapters.security.google_oauth2_authenticator import GoogleOAuth2Authenticator
from backend_estudiantil.adapters.security.jwt_authenticator import JWTAuthenticator
from backend_estudiantil.config.settings import settings
from backend_estudiantil.domain.models.user import User
from backend_estudiantil.ports.repositories.user_repository import UserRepository
from backend_estudiantil.schemas.auth import Token

router = APIRouter(prefix="/auth/google", tags=["auth"])

def get_user_repository() -> UserRepository:
    return SQLAlchemyUserRepository()

def get_jwt_authenticator() -> JWTAuthenticator:
    return JWTAuthenticator()

def get_google_authenticator() -> GoogleOAuth2Authenticator:
    return GoogleOAuth2Authenticator()

@router.get("/login")
async def google_login(authenticator: GoogleOAuth2Authenticator = Depends(get_google_authenticator)):
    """Retorna la URL de autorización de Google OAuth2 para redirigir al usuario."""
    url = await authenticator.get_authorization_url()
    return {"authorization_url": url}

@router.get("/callback")
async def google_callback(
    code: str,
    response: Response,
    repo: UserRepository = Depends(get_user_repository),
    jwt_auth: JWTAuthenticator = Depends(get_jwt_authenticator),
    google_auth: GoogleOAuth2Authenticator = Depends(get_google_authenticator),
):
    """Callback de Google OAuth2. Intercambia el código por tokens y perfil."""
    token_data = await google_auth.exchange_code(code)
    access_token_google = token_data.get("access_token")
    if not access_token_google:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing access token from Google")

    userinfo = await google_auth.get_userinfo(access_token_google)
    email = userinfo.get("email")
    name = userinfo.get("name")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account has no email")

    # Si no existe, crear al usuario automáticamente
    user = await repo.get_by_email(email)
    now = datetime.now(timezone.utc)
    if not user:
        user = User(
            id=str(uuid4()),
            email=email,
            hashed_password="",  # Sin contraseña para usuarios federados con Google
            name=name,
            created_at=now,
            updated_at=now,
            role="user",
            is_active=True,
        )
        await repo.create(user)

    # Emitir tokens JWT
    role = getattr(user, "role", "user")
    payload = {"sub": user.id, "role": role}
    access_jwt = jwt_auth.create_access_token(payload)
    refresh_jwt = jwt_auth.create_refresh_token(payload)

    # Setear cookie segura de refresh token
    response.set_cookie(
        key="refresh_token",
        value=refresh_jwt,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )
    return Token(
        access_token=access_jwt,
        token_type="bearer",
        role=role,
        expires_in=float(60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
