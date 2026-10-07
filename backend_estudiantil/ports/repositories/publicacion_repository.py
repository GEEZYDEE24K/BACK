from abc import ABC, abstractmethod
from typing import List, Optional
from backend_estudiantil.domain.models.publicacion import Publicacion

class PublicacionRepository(ABC):
    """Puerto para la persistencia de publicaciones."""

    @abstractmethod
    async def get_by_id(self, publicacion_id: int) -> Optional[Publicacion]:
        ...

    @abstractmethod
    async def list_activas(self, skip: int = 0, limit: int = 50, categoria_id: Optional[int] = None, busqueda: Optional[str] = None) -> List[Publicacion]:
        ...

    @abstractmethod
    async def list_by_usuario(self, usuario_id: int) -> List[Publicacion]:
        ...

    @abstractmethod
    async def create(self, publicacion: Publicacion) -> Publicacion:
        ...

    @abstractmethod
    async def update(self, publicacion: Publicacion) -> Publicacion:
        ...

    @abstractmethod
    async def delete(self, publicacion_id: int) -> None:
        ...
