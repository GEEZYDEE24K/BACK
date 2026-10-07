from abc import ABC, abstractmethod
from typing import List, Optional
from backend_estudiantil.domain.models.match import Match

class MatchRepository(ABC):
    """Puerto para la persistencia de coincidencias (matches)."""

    @abstractmethod
    async def get_by_id(self, match_id: int) -> Optional[Match]:
        ...

    @abstractmethod
    async def list_by_usuario(self, usuario_id: int) -> List[Match]:
        ...

    @abstractmethod
    async def create(self, match: Match) -> Match:
        ...

    @abstractmethod
    async def get_existing_match(self, origen_id: int, destino_id: int) -> Optional[Match]:
        ...
