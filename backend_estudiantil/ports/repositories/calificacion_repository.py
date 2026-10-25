from abc import ABC, abstractmethod
from typing import List, Optional
from backend_estudiantil.domain.models.calificacion import Calificacion

class CalificacionRepository(ABC):
    """Puerto para la persistencia de valoraciones y reputación."""

    @abstractmethod
    async def get_by_id(self, calificacion_id: int) -> Optional[Calificacion]:
        ...

    @abstractmethod
    async def list_by_usuario_calificado(self, usuario_id: int) -> List[Calificacion]:
        ...

    @abstractmethod
    async def get_by_trueque_and_calificador(self, trueque_id: int, calificador_id: int) -> Optional[Calificacion]:
        ...

    @abstractmethod
    async def create(self, calificacion: Calificacion) -> Calificacion:
        ...
