import os
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn

class Settings(BaseSettings):
    # La URL de conexión se genera dinámicamente a partir de CONNECTIONSTRINGS y DATABASEPROVIDER

    # JWT settings
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    # Cookie settings
    COOKIE_SECURE: bool = Field(default=True, env="COOKIE_SECURE")
    COOKIE_HTTPONLY: bool = Field(default=True, env="COOKIE_HTTPONLY")
    COOKIE_SAMESITE: str = Field(default="Strict", env="COOKIE_SAMESITE")

    # Google OAuth2 settings
    GOOGLE_CLIENT_ID: str = Field(default="", env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", env="GOOGLE_CLIENT_SECRET")
    GOOGLE_SCOPES: str = Field(default="openid email profile", env="GOOGLE_SCOPES")
    # Configuración avanzada (según solicitud)
    JWT_KEY: str = Field(default="MySuperSecretKey1234567890!@#$%^&*()_+", env="JWT_KEY")
    JWT_ISSUER: str = Field(default="MyApp", env="JWT_ISSUER")
    JWT_AUDIENCE: str = Field(default="MyAppUsers", env="JWT_AUDIENCE")
    JWT_DURACION_MINUTOS: int = Field(default=60, env="JWT_DURACION_MINUTOS")
    TABLAS_PROHIBIDAS: list[str] = Field(default_factory=list, env="TABLAS_PROHIBIDAS")
    CONNECTIONSTRINGS: dict[str, str] = Field(
        default_factory=lambda: {
            "SqlServer": "Server=MI_SERVIDOR;Database=mi_bd;Integrated Security=True;TrustServerCertificate=True;",
            "LocalDb": "Server=(localdb)\\MSSQLLocalDB;Database=mi_bd;Integrated Security=True;TrustServerCertificate=True;",
            "Postgres": "Host=localhost;Port=5432;Database=trueque;Username=postgres;Password=123456;Pooling=true;Maximum Pool Size=100;",
            "MariaDB": "Server=localhost;Port=3306;Database=mi_bd;User=root;Password=;",
            "MySQL": "Server=localhost;Port=3306;Database=mi_bd;User=root;Password=mysql;CharSet=utf8mb4;",
        },
        env="CONNECTIONSTRINGS",
    )
    DATABASEPROVIDER: str = Field(default="Postgres", env="DATABASEPROVIDER")

    @property
    def DATABASE_URL(self) -> str:
        """Devuelve la cadena de conexión correspondiente al provider seleccionado."""
        return self.CONNECTIONSTRINGS.get(self.DATABASEPROVIDER, "")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
