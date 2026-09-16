import uuid
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend_estudiantil.adapters.db import UserORM, AsyncSessionLocal
from backend_estudiantil.domain.models.user import User
from backend_estudiantil.ports.repositories.user_repository import UserRepository

class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of the UserRepository port."""

    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def _to_entity(self, orm: UserORM) -> User:
        return User(
            id=orm.id,
            email=orm.email,
            hashed_password=orm.hashed_password,
            name=orm.name,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            role=orm.role,
        )

    async def get_by_id(self, user_id: str) -> Optional[User]:
        async with self.session_factory() as session:
            result = await session.execute(select(UserORM).where(UserORM.id == user_id))
            orm = result.scalar_one_or_none()
            return await self._to_entity(orm) if orm else None

    async def get_by_email(self, email: str) -> Optional[User]:
        async with self.session_factory() as session:
            result = await session.execute(select(UserORM).where(UserORM.email == email))
            orm = result.scalar_one_or_none()
            return await self._to_entity(orm) if orm else None

    async def create(self, user: User) -> User:
        async with self.session_factory() as session:
            orm = UserORM(
                id=user.id,
                email=user.email,
                hashed_password=user.hashed_password,
                name=user.name,
                created_at=user.created_at,
                updated_at=user.updated_at,
                role=user.role,
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
            return await self._to_entity(orm)

    async def update(self, user: User) -> User:
        async with self.session_factory() as session:
            result = await session.execute(select(UserORM).where(UserORM.id == user.id))
            orm = result.scalar_one_or_none()
            if not orm:
                raise ValueError("User not found for update")
            orm.email = user.email
            orm.hashed_password = user.hashed_password
            orm.name = user.name
            orm.updated_at = user.updated_at
            await session.commit()
            await session.refresh(orm)
            return await self._to_entity(orm)

    async def delete(self, user_id: str) -> None:
        async with self.session_factory() as session:
            result = await session.execute(select(UserORM).where(UserORM.id == user_id))
            orm = result.scalar_one_or_none()
            if orm:
                await session.delete(orm)
                await session.commit()
