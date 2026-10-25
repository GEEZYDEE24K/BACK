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
    async def create_from_publications(
        self,
        usuario_propone_id: int,
        publicacion_origen_id: int,
        publicacion_destino_id: int,
        usuario_recibe_id: Optional[int] = None,
    ) -> Trueque:
        ...

    @abstractmethod
    async def create_from_match(
        self, usuario_propone_id: int, match_id: int, usuario_recibe_id: Optional[int] = None
    ) -> Trueque:
        ...

    @abstractmethod
    async def update(self, trueque: Trueque) -> Trueque:
        ...
