from datetime import datetime, timezone
from typing import Optional

class Calificacion:
    """Entidad de dominio que representa la valoración post-trueque entre estudiantes."""

    def __init__(
        self,
        id: Optional[int] = None,
        trueque_id: int = 0,
        usuario_califica_id: int = 0,
        usuario_calificado_id: int = 0,
        estrellas: int = 5,
        resena: Optional[str] = None,
        fecha_calificacion: Optional[datetime] = None,
    ):
        if estrellas < 1 or estrellas > 5:
            raise ValueError("La calificación debe estar entre 1 y 5 estrellas")
        self.id = id
        self.trueque_id = trueque_id
        self.usuario_califica_id = usuario_califica_id
        self.usuario_calificado_id = usuario_calificado_id
        self.estrellas = estrellas
        self.resena = resena
        self.fecha_calificacion = fecha_calificacion or datetime.now(timezone.utc)
