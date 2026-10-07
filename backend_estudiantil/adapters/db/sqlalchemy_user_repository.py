from typing import List, Optional
from sqlalchemy.future import select

from backend_estudiantil.adapters.db import UserORM, get_session_factory
from backend_estudiantil.domain.models.user import User
from backend_estudiantil.ports.repositories.user_repository import UserRepository

class SQLAlchemyUserRepository(UserRepository):
    """Implementación en SQLAlchemy del repositorio de usuarios sobre la tabla 'usuarios'."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    @property
    def session_factory(self):
        return self._session_factory if self._session_factory is not None else get_session_factory()

    async def _to_entity(self, orm: UserORM) -> User:
        return User(
            id=orm.id,
            nombre=orm.nombre,
            apellido=orm.apellido,
            correo_institucional=orm.correo_institucional,
            password_hash=orm.password_hash,
            tipo_usuario=getattr(orm, "tipo_usuario", "estudiante"),
            programa_area=getattr(orm, "programa_area", None),
            rol=getattr(orm, "rol", "usuario"),
            verificado_comunidad=getattr(orm, "verificado_comunidad", True),
            estado_cuenta=getattr(orm, "estado_cuenta", "activo"),
            fecha_registro=orm.fecha_registro,
        )

    async def get_by_id(self, user_id) -> Optional[User]:
        async with self.session_factory() as session:
            try:
                uid = int(user_id)
                result = await session.execute(select(UserORM).where(UserORM.id == uid))
            except (ValueError, TypeError):
                result = await session.execute(select(UserORM).where(UserORM.correo_institucional == str(user_id)))
            orm = result.scalar_one_or_none()
            return await self._to_entity(orm) if orm else None

    async def get_by_email(self, email: str) -> Optional[User]:
        async with self.session_factory() as session:
            result = await session.execute(select(UserORM).where(UserORM.correo_institucional == email))
            orm = result.scalar_one_or_none()
            return await self._to_entity(orm) if orm else None

    async def create(self, user: User) -> User:
        async with self.session_factory() as session:
            orm = UserORM(
                nombre=user.nombre or "Estudiante",
                apellido=user.apellido or "",
                correo_institucional=user.correo_institucional,
                password_hash=user.password_hash,
                tipo_usuario=user.tipo_usuario or "estudiante",
                programa_area=user.programa_area,
                rol=user.rol or "usuario",
                verificado_comunidad=user.verificado_comunidad,
                estado_cuenta=user.estado_cuenta or "activo",
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
            return await self._to_entity(orm)

    async def update(self, user: User) -> User:
        async with self.session_factory() as session:
            uid = int(user.id)
            result = await session.execute(select(UserORM).where(UserORM.id == uid))
            orm = result.scalar_one_or_none()
            if not orm:
                raise ValueError("User not found for update")
            orm.nombre = user.nombre
            orm.apellido = user.apellido
            orm.correo_institucional = user.correo_institucional
            orm.password_hash = user.password_hash
            orm.rol = user.rol
            orm.estado_cuenta = user.estado_cuenta
            orm.programa_area = user.programa_area
            await session.commit()
            await session.refresh(orm)
            return await self._to_entity(orm)

    async def delete(self, user_id) -> None:
        async with self.session_factory() as session:
            try:
                uid = int(user_id)
                result = await session.execute(select(UserORM).where(UserORM.id == uid))
            except (ValueError, TypeError):
                result = await session.execute(select(UserORM).where(UserORM.correo_institucional == str(user_id)))
            orm = result.scalar_one_or_none()
            if orm:
                await session.delete(orm)
                await session.commit()

    async def list(self, skip: int = 0, limit: int = 100) -> List[User]:
        async with self.session_factory() as session:
            result = await session.execute(select(UserORM).offset(skip).limit(limit))
            orms = result.scalars().all()
            return [await self._to_entity(o) for o in orms]
