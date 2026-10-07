from datetime import datetime, timezone
from typing import Optional

class Trueque:
    """Entidad de dominio que gestiona el estado y ciclo de vida de un intercambio de libros."""

    def __init__(
        self,
        id: Optional[int] = None,
        match_id: Optional[int] = None,
        usuario_propone_id: int = 0,
        usuario_recibe_id: int = 0,
        estado: str = "propuesto",
        fecha_propuesta: Optional[datetime] = None,
        fecha_confirmacion: Optional[datetime] = None,
        fecha_completado: Optional[datetime] = None,
    ):
        self.id = id
        self.match_id = match_id
        self.usuario_propone_id = usuario_propone_id
        self.usuario_recibe_id = usuario_recibe_id
        self.estado = estado
        self.fecha_propuesta = fecha_propuesta or datetime.now(timezone.utc)
        self.fecha_confirmacion = fecha_confirmacion
        self.fecha_completado = fecha_completado

    def confirmar(self):
        if self.estado != "propuesto":
            raise ValueError(f"No se puede confirmar un trueque en estado '{self.estado}'")
        self.estado = "confirmado"
        self.fecha_confirmacion = datetime.now(timezone.utc)

    def completar(self):
        if self.estado not in ("propuesto", "confirmado"):
            raise ValueError(f"No se puede completar un trueque en estado '{self.estado}'")
        self.estado = "completado"
        self.fecha_completado = datetime.now(timezone.utc)

    def rechazar(self):
        if self.estado == "completado":
            raise ValueError("Un trueque completado no puede ser rechazado")
        self.estado = "rechazado"
