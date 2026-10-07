from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.future import select

from backend_estudiantil.adapters.db import TruequeORM, get_session_factory
from backend_estudiantil.domain.models.trueque import Trueque
from backend_estudiantil.ports.repositories.trueque_repository import TruequeRepository


class SQLAlchemyTruequeRepository(TruequeRepository):
    """Implementación SQLAlchemy del repositorio de trueques sobre la tabla 'trueques'."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    @property
    def session_factory(self):
        return self._session_factory if self._session_factory is not None else get_session_factory()

    def _to_entity(self, orm: TruequeORM) -> Trueque:
        return Trueque(
            id=orm.id,
            match_id=orm.match_id,
            usuario_propone_id=orm.usuario_propone_id,
            usuario_recibe_id=orm.usuario_recibe_id,
            estado=orm.estado,
            fecha_propuesta=orm.fecha_propuesta,
            fecha_confirmacion=orm.fecha_confirmacion,
            fecha_completado=orm.fecha_completado,
        )

    async def get_by_id(self, trueque_id: int) -> Optional[Trueque]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(TruequeORM).where(TruequeORM.id == trueque_id)
            )
            orm = result.scalar_one_or_none()
            return self._to_entity(orm) if orm else None

    async def list_by_usuario(self, usuario_id: int, estado: Optional[str] = None) -> List[Trueque]:
        """Retorna trueques en los que el usuario participa (como proponente o receptor)."""
        async with self.session_factory() as session:
            from sqlalchemy import or_
            query = select(TruequeORM).where(
                or_(
                    TruequeORM.usuario_propone_id == usuario_id,
                    TruequeORM.usuario_recibe_id == usuario_id,
                )
            )
            if estado:
                query = query.where(TruequeORM.estado == estado)
            result = await session.execute(query)
            orms = result.scalars().all()
            return [self._to_entity(o) for o in orms]

    async def create(self, trueque: Trueque) -> Trueque:
        async with self.session_factory() as session:
            orm = TruequeORM(
                match_id=trueque.match_id,
                usuario_propone_id=trueque.usuario_propone_id,
                usuario_recibe_id=trueque.usuario_recibe_id,
                estado=trueque.estado,
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
            return self._to_entity(orm)

    async def update(self, trueque: Trueque) -> Trueque:
        async with self.session_factory() as session:
            result = await session.execute(
                select(TruequeORM).where(TruequeORM.id == trueque.id)
            )
            orm = result.scalar_one_or_none()
            if not orm:
                raise ValueError("Trueque no encontrado para actualizar")
            orm.estado = trueque.estado
            orm.fecha_confirmacion = trueque.fecha_confirmacion
            orm.fecha_completado = trueque.fecha_completado
            await session.commit()
            await session.refresh(orm)
            return self._to_entity(orm)
