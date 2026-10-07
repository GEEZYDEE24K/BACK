from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class MatchRead(BaseModel):
    id: int
    publicacion_origen_id: int
    publicacion_destino_id: int
    tipo_match: str = Field(description="Tipo: exacta, parcial")
    puntuacion: float = Field(description="Puntuación de coincidencia entre 0 y 100")
    fecha_creacion: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TruequeCreate(BaseModel):
    usuario_recibe_id: int = Field(..., description="ID del usuario que recibirá la propuesta")
    match_id: Optional[int] = Field(None, description="ID del match asociado (opcional)")


class TruequeAccion(BaseModel):
    accion: str = Field(..., description="Acción a ejecutar: confirmar, completar, rechazar")


class TruequeRead(BaseModel):
    id: int
    match_id: Optional[int] = None
    usuario_propone_id: int
    usuario_recibe_id: int
    estado: str
    fecha_propuesta: Optional[datetime] = None
    fecha_confirmacion: Optional[datetime] = None
    fecha_completado: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CalificacionCreate(BaseModel):
    usuario_calificado_id: int = Field(..., description="ID del usuario que se va a calificar")
    estrellas: int = Field(..., ge=1, le=5, description="Calificación de 1 a 5 estrellas")
    resena: Optional[str] = Field(None, max_length=500, description="Reseña opcional del intercambio")


class CalificacionRead(BaseModel):
    id: int
    trueque_id: int
    usuario_califica_id: int
    usuario_calificado_id: int
    estrellas: int
    resena: Optional[str] = None
    fecha_calificacion: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReputacionRead(BaseModel):
    usuario_id: int
    promedio_estrellas: Optional[float] = None
    total_calificaciones: int
    calificaciones: list
