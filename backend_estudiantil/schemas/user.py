from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Correo electrónico del usuario")
    name: Optional[str] = Field(None, description="Nombre completo del estudiante")
    telefono: Optional[str] = Field(None, description="Número de teléfono o WhatsApp de contacto")
    carrera: Optional[str] = Field(None, description="Carrera o programa académico")
    universidad: Optional[str] = Field(None, description="Universidad o campus del estudiante")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Contraseña de acceso (mínimo 6 caracteres)")
    role: Optional[str] = Field(default="user", description="Rol del usuario ('admin', 'moderador', 'user')")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    telefono: Optional[str] = None
    carrera: Optional[str] = None
    universidad: Optional[str] = None

class UserRead(UserBase):
    id: str
    role: str = Field(default="user", description="Rol asignado al usuario")
    is_active: bool = Field(default=True, description="Estado de la cuenta")
    created_at: str = Field(..., description="Fecha de creación ISO 8601")
    updated_at: str = Field(..., description="Fecha de última actualización ISO 8601")

    model_config = ConfigDict(from_attributes=True)
