from typing import List, Optional

from backend_estudiantil.domain.models.trueque import Trueque
from backend_estudiantil.ports.repositories.trueque_repository import TruequeRepository


class TruequeService:
    """
    Servicio de dominio para la gestión del ciclo de vida de los trueques.
    Maneja las transiciones de estado: propuesto → confirmado → completado / rechazado.
    """

    ESTADOS_VALIDOS = {"propuesto", "confirmado", "completado", "rechazado"}

    def __init__(self, repo: TruequeRepository):
        self.repo = repo

    async def proponer_trueque(
        self,
        usuario_propone_id: int,
        usuario_recibe_id: int,
        match_id: Optional[int] = None,
    ) -> Trueque:
        """Crea una nueva propuesta de trueque entre dos usuarios."""
        if usuario_propone_id == usuario_recibe_id:
            raise ValueError("Un usuario no puede proponer un trueque consigo mismo")

        trueque = Trueque(
            match_id=match_id,
            usuario_propone_id=usuario_propone_id,
            usuario_recibe_id=usuario_recibe_id,
            estado="propuesto",
        )
        return await self.repo.create(trueque)

    async def obtener_trueque(self, trueque_id: int) -> Trueque:
        trueque = await self.repo.get_by_id(trueque_id)
        if not trueque:
            raise ValueError(f"Trueque {trueque_id} no encontrado")
        return trueque

    async def listar_trueques_usuario(
        self, usuario_id: int, estado: Optional[str] = None
    ) -> List[Trueque]:
        if estado and estado not in self.ESTADOS_VALIDOS:
            raise ValueError(f"Estado inválido: {estado}. Válidos: {self.ESTADOS_VALIDOS}")
        return await self.repo.list_by_usuario(usuario_id, estado=estado)

    async def confirmar_trueque(self, trueque_id: int, usuario_id: int) -> Trueque:
        """El usuario receptor confirma la propuesta de trueque."""
        trueque = await self.obtener_trueque(trueque_id)
        if trueque.usuario_recibe_id != usuario_id:
            raise PermissionError("Solo el usuario receptor puede confirmar el trueque")
        trueque.confirmar()
        return await self.repo.update(trueque)

    async def completar_trueque(self, trueque_id: int, usuario_id: int) -> Trueque:
        """Cualquier participante puede marcar el trueque como completado."""
        trueque = await self.obtener_trueque(trueque_id)
        if usuario_id not in (trueque.usuario_propone_id, trueque.usuario_recibe_id):
            raise PermissionError("Solo los participantes del trueque pueden completarlo")
        trueque.completar()
        return await self.repo.update(trueque)

    async def rechazar_trueque(self, trueque_id: int, usuario_id: int) -> Trueque:
        """El usuario receptor puede rechazar la propuesta."""
        trueque = await self.obtener_trueque(trueque_id)
        if usuario_id not in (trueque.usuario_propone_id, trueque.usuario_recibe_id):
            raise PermissionError("Solo los participantes pueden rechazar el trueque")
        trueque.rechazar()
        return await self.repo.update(trueque)
