from abc import ABC, abstractmethod
from typing import List, Optional
from backend_estudiantil.domain.models.user import User

class UserRepository(ABC):
    """Port (interface) for user persistence operations."""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        ...

    @abstractmethod
    async def create(self, user: User) -> User:
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        ...

    @abstractmethod
    async def delete(self, user_id: str) -> None:
        ...
