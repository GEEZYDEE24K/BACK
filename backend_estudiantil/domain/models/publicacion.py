from datetime import datetime, timezone
from typing import Optional

class Publicacion:
    """Entidad de dominio que representa un libro o material ofertado o buscado."""

    def __init__(
        self,
        id: Optional[int] = None,
        usuario_id: int = 0,
        titulo: str = "",
        autor: Optional[str] = None,
        isbn: Optional[str] = None,
        edicion: Optional[str] = None,
        categoria_id: Optional[int] = None,
        estado_libro: Optional[str] = None,
        descripcion: Optional[str] = None,
        libro_buscado: Optional[str] = None,
        estado_publicacion: str = "activa",
        fecha_publicacion: Optional[datetime] = None,
    ):
        self.id = id
        self.usuario_id = usuario_id
        self.titulo = titulo
        self.autor = autor
        self.isbn = isbn
        self.edicion = edicion
        self.categoria_id = categoria_id
        self.estado_libro = estado_libro or "Buen estado"
        self.descripcion = descripcion
        self.libro_buscado = libro_buscado
        self.estado_publicacion = estado_publicacion
        self.fecha_publicacion = fecha_publicacion or datetime.now(timezone.utc)
