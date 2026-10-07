from abc import ABC, abstractmethod
from typing import List, Optional
from backend_estudiantil.domain.models.trueque import Trueque

class TruequeRepository(ABC):
    """Puerto para la persistencia de trueques."""

    @abstractmethod
    async def get_by_id(self, trueque_id: int) -> Optional[Trueque]:
        ...

    @abstractmethod
    async def list_by_usuario(self, usuario_id: int, estado: Optional[str] = None) -> List[Trueque]:
        ...

    @abstractmethod
    async def create(self, trueque: Trueque) -> Trueque:
        ...

    @abstractmethod
    async def update(self, trueque: Trueque) -> Trueque:
        ...
