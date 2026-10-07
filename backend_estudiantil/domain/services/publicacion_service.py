from typing import List, Optional

from backend_estudiantil.domain.models.publicacion import Publicacion
from backend_estudiantil.ports.repositories.publicacion_repository import PublicacionRepository


class PublicacionService:
    """Servicio de dominio para la lógica de negocio de publicaciones de libros/materiales."""

    def __init__(self, repo: PublicacionRepository):
        self.repo = repo

    async def crear_publicacion(
        self,
        usuario_id: int,
        titulo: str,
        autor: Optional[str] = None,
        isbn: Optional[str] = None,
        edicion: Optional[str] = None,
        categoria_id: Optional[int] = None,
        estado_libro: Optional[str] = None,
        descripcion: Optional[str] = None,
        libro_buscado: Optional[str] = None,
    ) -> Publicacion:
        """Crea una nueva publicación de libro o material académico."""
        if not titulo or not titulo.strip():
            raise ValueError("El título de la publicación es obligatorio")

        publicacion = Publicacion(
            usuario_id=usuario_id,
            titulo=titulo.strip(),
            autor=autor,
            isbn=isbn,
            edicion=edicion,
            categoria_id=categoria_id,
            estado_libro=estado_libro or "Buen estado",
            descripcion=descripcion,
            libro_buscado=libro_buscado,
            estado_publicacion="activa",
        )
        return await self.repo.create(publicacion)

    async def obtener_publicacion(self, publicacion_id: int) -> Publicacion:
        pub = await self.repo.get_by_id(publicacion_id)
        if not pub:
            raise ValueError(f"Publicación {publicacion_id} no encontrada")
        return pub

    async def listar_publicaciones(
        self,
        skip: int = 0,
        limit: int = 50,
        categoria_id: Optional[int] = None,
        busqueda: Optional[str] = None,
    ) -> List[Publicacion]:
        return await self.repo.list_activas(skip=skip, limit=limit, categoria_id=categoria_id, busqueda=busqueda)

    async def listar_por_usuario(self, usuario_id: int) -> List[Publicacion]:
        return await self.repo.list_by_usuario(usuario_id)

    async def actualizar_publicacion(
        self,
        publicacion_id: int,
        usuario_id: int,
        datos: dict,
    ) -> Publicacion:
        """Actualiza una publicación. Solo el dueño puede modificarla."""
        pub = await self.obtener_publicacion(publicacion_id)
        if pub.usuario_id != usuario_id:
            raise PermissionError("No tienes permiso para editar esta publicación")

        for campo, valor in datos.items():
            if hasattr(pub, campo) and valor is not None:
                setattr(pub, campo, valor)

        return await self.repo.update(pub)

    async def desactivar_publicacion(self, publicacion_id: int, usuario_id: int) -> Publicacion:
        """Cambia el estado de la publicación a 'inactiva'."""
        pub = await self.obtener_publicacion(publicacion_id)
        if pub.usuario_id != usuario_id:
            raise PermissionError("No tienes permiso para eliminar esta publicación")
        pub.estado_publicacion = "inactiva"
        return await self.repo.update(pub)

    async def eliminar_publicacion(self, publicacion_id: int, usuario_id: int) -> None:
        """Elimina físicamente una publicación (solo el dueño)."""
        pub = await self.obtener_publicacion(publicacion_id)
        if pub.usuario_id != usuario_id:
            raise PermissionError("No tienes permiso para eliminar esta publicación")
        await self.repo.delete(publicacion_id)
