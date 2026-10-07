from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import or_, cast, String


from backend_estudiantil.adapters.db import PublicacionORM, get_session_factory
from backend_estudiantil.domain.models.publicacion import Publicacion
from backend_estudiantil.ports.repositories.publicacion_repository import PublicacionRepository


class SQLAlchemyPublicacionRepository(PublicacionRepository):
    """Implementación SQLAlchemy del repositorio de publicaciones sobre la tabla 'publicaciones'."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    @property
    def session_factory(self):
        return self._session_factory if self._session_factory is not None else get_session_factory()

    def _to_entity(self, orm: PublicacionORM) -> Publicacion:
        return Publicacion(
            id=orm.id,
            usuario_id=orm.usuario_id,
            titulo=orm.titulo,
            autor=orm.autor,
            isbn=orm.isbn,
            edicion=orm.edicion,
            categoria_id=orm.categoria_id,
            estado_libro=orm.estado_libro,
            descripcion=orm.descripcion,
            libro_buscado=orm.libro_buscado,
            estado_publicacion=orm.estado_publicacion,
            fecha_publicacion=orm.fecha_publicacion,
        )

    async def get_by_id(self, publicacion_id: int) -> Optional[Publicacion]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(PublicacionORM).where(PublicacionORM.id == publicacion_id)
            )
            orm = result.scalar_one_or_none()
            return self._to_entity(orm) if orm else None

    async def list_activas(
        self,
        skip: int = 0,
        limit: int = 50,
        categoria_id: Optional[int] = None,
        busqueda: Optional[str] = None,
    ) -> List[Publicacion]:
        async with self.session_factory() as session:
            query = select(PublicacionORM).where(cast(PublicacionORM.estado_publicacion, String) == "activa")


            if categoria_id is not None:
                query = query.where(PublicacionORM.categoria_id == categoria_id)

            if busqueda:
                patron = f"%{busqueda}%"
                query = query.where(
                    or_(
                        PublicacionORM.titulo.ilike(patron),
                        PublicacionORM.autor.ilike(patron),
                        PublicacionORM.libro_buscado.ilike(patron),
                        PublicacionORM.descripcion.ilike(patron),
                    )
                )

            query = query.offset(skip).limit(limit)
            result = await session.execute(query)
            orms = result.scalars().all()
            return [self._to_entity(o) for o in orms]

    async def list_by_usuario(self, usuario_id: int) -> List[Publicacion]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(PublicacionORM).where(PublicacionORM.usuario_id == usuario_id)
            )
            orms = result.scalars().all()
            return [self._to_entity(o) for o in orms]

    async def create(self, publicacion: Publicacion) -> Publicacion:
        async with self.session_factory() as session:
            orm = PublicacionORM(
                usuario_id=publicacion.usuario_id,
                titulo=publicacion.titulo,
                autor=publicacion.autor,
                isbn=publicacion.isbn,
                edicion=publicacion.edicion,
                categoria_id=publicacion.categoria_id,
                estado_libro=publicacion.estado_libro,
                descripcion=publicacion.descripcion,
                libro_buscado=publicacion.libro_buscado,
                estado_publicacion=publicacion.estado_publicacion,
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
            return self._to_entity(orm)

    async def update(self, publicacion: Publicacion) -> Publicacion:
        async with self.session_factory() as session:
            result = await session.execute(
                select(PublicacionORM).where(PublicacionORM.id == publicacion.id)
            )
            orm = result.scalar_one_or_none()
            if not orm:
                raise ValueError("Publicación no encontrada para actualizar")
            orm.titulo = publicacion.titulo
            orm.autor = publicacion.autor
            orm.isbn = publicacion.isbn
            orm.edicion = publicacion.edicion
            orm.categoria_id = publicacion.categoria_id
            orm.estado_libro = publicacion.estado_libro
            orm.descripcion = publicacion.descripcion
            orm.libro_buscado = publicacion.libro_buscado
            orm.estado_publicacion = publicacion.estado_publicacion
            await session.commit()
            await session.refresh(orm)
            return self._to_entity(orm)

    async def delete(self, publicacion_id: int) -> None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(PublicacionORM).where(PublicacionORM.id == publicacion_id)
            )
            orm = result.scalar_one_or_none()
            if orm:
                await session.delete(orm)
                await session.commit()
