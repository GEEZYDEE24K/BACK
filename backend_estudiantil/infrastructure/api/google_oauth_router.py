from fastapi import APIRouter, Depends, HTTPException, Response, status
from backend_estudiantil.adapters.security.google_oauth2_authenticator import GoogleOAuth2Authenticator
from backend_estudiantil.adapters.security.jwt_authenticator import JWTAuthenticator
from backend_estudiantil.adapters.db.sqlalchemy_user_repository import SQLAlchemyUserRepository
from backend_estudiantil.ports.repositories.user_repository import UserRepository
from backend_estudiantil.schemas.auth import Token
from backend_estudiantil.domain.models.user import User
from uuid import uuid4
from datetime import datetime
from backend_estudiantil.config.settings import settings

router = APIRouter(prefix="/auth/google", tags=["auth"])

def get_user_repository() -> UserRepository:
    return SQLAlchemyUserRepository()

def get_jwt_authenticator() -> JWTAuthenticator:
    return JWTAuthenticator()

def get_google_authenticator() -> GoogleOAuth2Authenticator:
    return GoogleOAuth2Authenticator()

@router.get("/login")
async def google_login(authenticator: GoogleOAuth2Authenticator = Depends(get_google_authenticator)):
    """Return the Google OAuth2 authorization URL.
    The client should be redirected to this URL.
    """
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
    """Handle Google OAuth2 callback.
    Exchanges ``code`` for access token, fetches user info, creates the user
    if it does not exist, and returns JWT ``Token`` with a refresh‑token cookie.
    """
    token_data = await google_auth.exchange_code(code)
    access_token_google = token_data.get("access_token")
    if not access_token_google:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing access token from Google")
    userinfo = await google_auth.get_userinfo(access_token_google)
    email = userinfo.get("email")
    name = userinfo.get("name")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account has no email")
    # Check if user exists, otherwise create automatically (role defaults to "user")
    user = await repo.get_by_email(email)
    if not user:
        user = User(
            id=str(uuid4()),
            email=email,
            hashed_password="",  # No password for Google‑based users
            name=name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            role="user",
        )
        await repo.create(user)
    # Issue JWT tokens including role
    payload = {"sub": user.id, "role": getattr(user, "role", "user")}
    access_jwt = jwt_auth.create_access_token(payload)
    refresh_jwt = jwt_auth.create_refresh_token(payload)
    # Set refresh‑token cookie (same policy as regular login)
    response.set_cookie(
        key="refresh_token",
        value=refresh_jwt,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )
    return Token(
        access_token=access_jwt,
        token_type="bearer",
        role=payload["role"],
        expires_in=60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
