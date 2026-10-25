import os
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings
# pyrefly: ignore [missing-import]
from pydantic import Field, ConfigDict

class Settings(BaseSettings):
    """Configuración global de la aplicación Trueque Estudiantil."""

    # Configuración directa y visible de Base de Datos
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:123456@localhost:5432/trueque",
        validation_alias="DATABASE_URL",
        description="Cadena de conexión directa para SQLAlchemy Async (PostgreSQL o SQLite)",
    )

    REDIS_URL: str = Field(
        default="",
        validation_alias="REDIS_URL",
        description="Redis para distribuir eventos WebSocket entre réplicas de la API",
    )
    BOOK_VERIFICATION_STORAGE_PATH: str = Field(
        default="./storage/book-verification",
        validation_alias="BOOK_VERIFICATION_STORAGE_PATH",
        description="Directorio privado para fotos de verificación de publicaciones",
    )

    def get_database_url(self) -> str:
        """Obtiene la URL activa de conexión a base de datos."""
        return self.DATABASE_URL

    # JWT settings
    JWT_SECRET_KEY: str = Field(default="MySuperSecretKey1234567890!@#$%^&*()_+", validation_alias="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Cookie settings
    COOKIE_SECURE: bool = Field(default=False, validation_alias="COOKIE_SECURE")
    COOKIE_HTTPONLY: bool = Field(default=True, validation_alias="COOKIE_HTTPONLY")
    COOKIE_SAMESITE: str = Field(default="lax", validation_alias="COOKIE_SAMESITE")

    # Google OAuth2 settings
    GOOGLE_CLIENT_ID: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", validation_alias="GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = Field(
        default="http://localhost:8000/auth/google/callback",
        validation_alias="GOOGLE_REDIRECT_URI",
    )
    GOOGLE_SCOPES: str = Field(default="openid email profile", validation_alias="GOOGLE_SCOPES")

    # Facebook OAuth2 settings
    FACEBOOK_CLIENT_ID: str = Field(default="", validation_alias="FACEBOOK_CLIENT_ID")
    FACEBOOK_CLIENT_SECRET: str = Field(default="", validation_alias="FACEBOOK_CLIENT_SECRET")
    FACEBOOK_REDIRECT_URI: str = Field(
        default="http://localhost:8000/auth/facebook/callback",
        validation_alias="FACEBOOK_REDIRECT_URI",
    )
    FACEBOOK_SCOPES: str = Field(default="email,public_profile", validation_alias="FACEBOOK_SCOPES")


    # Verificación de comunidad y dominios institucionales
    DOMINIOS_INSTITUCIONALES: dict[str, str] = Field(
        default={
            "unal.edu.co": "Universidad Nacional de Colombia",
            "udea.edu.co": "Universidad de Antioquia",
            "uniandes.edu.co": "Universidad de los Andes",
            "javeriana.edu.co": "Pontificia Universidad Javeriana",
            "univalle.edu.co": "Universidad del Valle",
            "udistrital.edu.co": "Universidad Distrital Francisco José de Caldas",
            "uis.edu.co": "Universidad Industrial de Santander",
            "uninpahu.edu.co": "UNINPAHU",
        },
        validation_alias="DOMINIOS_INSTITUCIONALES",
        description="Mapeo de dominios de correos institucionales a nombres de universidad",
    )

    # Configuración de Verificación con IA
    IA_UMBRAL_LIBRO: float = Field(
        default=0.10,
        validation_alias="IA_UMBRAL_LIBRO",
        description="Umbral de confianza mínima (0-1) para considerar una imagen como libro",
    )

    def es_dominio_institucional(self, email: str) -> bool:
        """Determina si un correo electrónico pertenece a un dominio universitario institucional."""
        if not email or "@" not in email:
            return False
        dominio = email.split("@")[-1].strip().lower()
        dominios_permitidos = {d.strip().lower() for d in self.DOMINIOS_INSTITUCIONALES.keys()}
        # Coincidencia exacta o subdominio institucional (ej. @alumno.unal.edu.co)
        return any(dominio == d or dominio.endswith(f".{d}") for d in dominios_permitidos)

    def obtener_universidad_por_dominio(self, email: str) -> str | None:
        """Retorna el nombre oficial de la universidad asociada al dominio del correo."""
        if not email or "@" not in email:
            return None
        dominio = email.split("@")[-1].strip().lower()
        for d, u in self.DOMINIOS_INSTITUCIONALES.items():
            d_lower = d.strip().lower()
            if dominio == d_lower or dominio.endswith(f".{d_lower}"):
                return u
        return None

    # Configuración avanzada
    JWT_KEY: str = Field(default="MySuperSecretKey1234567890!@#$%^&*()_+", validation_alias="JWT_KEY")
    JWT_ISSUER: str = Field(default="PlataformaTrueque", validation_alias="JWT_ISSUER")
    JWT_AUDIENCE: str = Field(default="Estudiantes", validation_alias="JWT_AUDIENCE")
    JWT_DURACION_MINUTOS: int = Field(default=60, validation_alias="JWT_DURACION_MINUTOS")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
