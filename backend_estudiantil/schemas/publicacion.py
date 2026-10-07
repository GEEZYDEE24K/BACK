from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class PublicacionBase(BaseModel):
    titulo: str = Field(..., description="Título del libro o material académico")
    autor: Optional[str] = Field(None, description="Autor del libro")
    isbn: Optional[str] = Field(None, description="ISBN del libro (si aplica)")
    edicion: Optional[str] = Field(None, description="Edición del libro")
    categoria_id: Optional[int] = Field(None, description="ID de la categoría académica")
    estado_libro: Optional[str] = Field(None, description="Estado físico del libro (Nuevo, Buen estado, Regular, etc.)")
    descripcion: Optional[str] = Field(None, description="Descripción detallada de la publicación")
    libro_buscado: Optional[str] = Field(None, description="Nombre del libro que se busca a cambio")


class PublicacionCreate(PublicacionBase):
    pass


class PublicacionUpdate(BaseModel):
    titulo: Optional[str] = None
    autor: Optional[str] = None
    isbn: Optional[str] = None
    edicion: Optional[str] = None
    categoria_id: Optional[int] = None
    estado_libro: Optional[str] = None
    descripcion: Optional[str] = None
    libro_buscado: Optional[str] = None
    estado_publicacion: Optional[str] = Field(None, description="Estado: activa, inactiva, completada")


class PublicacionRead(PublicacionBase):
    id: int
    usuario_id: int
    estado_publicacion: str
    fecha_publicacion: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CategoriaRead(BaseModel):
    id: int
    nombre: str

    model_config = ConfigDict(from_attributes=True)
