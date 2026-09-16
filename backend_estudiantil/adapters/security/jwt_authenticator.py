import jwt
from datetime import datetime, timedelta
from typing import Any, Dict

from backend_estudiantil.config.settings import settings
from backend_estudiantil.ports.security.authenticator import Authenticator

class JWTAuthenticator(Authenticator):
    """Concrete implementation of Authenticator using PyJWT.

    Tokens are signed with the secret key from settings and use the HS256 algorithm.
    Access tokens expire according to ``ACCESS_TOKEN_EXPIRE_MINUTES``.
    Refresh tokens expire according to ``REFRESH_TOKEN_EXPIRE_DAYS``.
    """

    def _create_token(self, data: Dict[str, Any], expires_delta: timedelta) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token

    def create_access_token(self, data: Dict[str, Any]) -> str:
        # Ensure role is present in token payload
        if "role" not in data:
            data["role"] = "user"
        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return self._create_token(data, expires)

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        # Ensure role is present in refresh token payload
        if "role" not in data:
            data["role"] = "user"
        expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        return self._create_token(data, expires)

    def decode_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError as exc:
            raise ValueError(f"Invalid token: {exc}")
