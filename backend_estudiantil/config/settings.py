import os
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn

class Settings(BaseSettings):
    # Database URL
    DATABASE_URL: PostgresDsn = Field(..., env="DATABASE_URL")

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
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
