from typing import List, Optional

from backend_estudiantil.domain.models.calificacion import Calificacion
from backend_estudiantil.domain.models.trueque import Trueque
from backend_estudiantil.ports.repositories.calificacion_repository import CalificacionRepository
from backend_estudiantil.ports.repositories.trueque_repository import TruequeRepository


class CalificacionService:
    """
    Servicio de dominio para la gestión de calificaciones y reputación.
    Solo se puede calificar un trueque completado y una vez por participante.
    """

    def __init__(self, calificacion_repo: CalificacionRepository, trueque_repo: TruequeRepository):
        self.calificacion_repo = calificacion_repo
        self.trueque_repo = trueque_repo

    async def calificar_trueque(
        self,
        trueque_id: int,
        usuario_califica_id: int,
        usuario_calificado_id: int,
        estrellas: int,
        resena: Optional[str] = None,
    ) -> Calificacion:
        """
        Registra una calificación post-trueque.
        - El trueque debe estar en estado 'completado'.
        - Solo los participantes del trueque pueden calificar.
        - Cada participante puede calificar al otro solo una vez.
        """
        trueque = await self.trueque_repo.get_by_id(trueque_id)
        if not trueque:
            raise ValueError(f"Trueque {trueque_id} no encontrado")

        if trueque.estado != "completado":
            raise ValueError(f"Solo se puede calificar un trueque completado. Estado actual: '{trueque.estado}'")

        participantes = {trueque.usuario_propone_id, trueque.usuario_recibe_id}
        if usuario_califica_id not in participantes:
            raise PermissionError("Solo los participantes del trueque pueden calificar")

        if usuario_calificado_id not in participantes:
            raise ValueError("El usuario calificado debe ser participante del trueque")

        if usuario_califica_id == usuario_calificado_id:
            raise ValueError("Un usuario no puede calificarse a sí mismo")

        # Verificar que no haya calificado ya
        existente = await self.calificacion_repo.get_by_trueque_and_calificador(
            trueque_id, usuario_califica_id
        )
        if existente:
            raise ValueError("Ya has calificado este trueque anteriormente")

        calificacion = Calificacion(
            trueque_id=trueque_id,
            usuario_califica_id=usuario_califica_id,
            usuario_calificado_id=usuario_calificado_id,
            estrellas=estrellas,
            resena=resena,
        )
        return await self.calificacion_repo.create(calificacion)

    async def obtener_reputacion_usuario(self, usuario_id: int) -> dict:
        """
        Calcula la reputación promedio de un usuario basada en sus calificaciones recibidas.
        """
        calificaciones = await self.calificacion_repo.list_by_usuario_calificado(usuario_id)

        if not calificaciones:
            return {
                "usuario_id": usuario_id,
                "promedio_estrellas": None,
                "total_calificaciones": 0,
                "calificaciones": [],
            }

        total = sum(c.estrellas for c in calificaciones)
        promedio = round(total / len(calificaciones), 2)

        return {
            "usuario_id": usuario_id,
            "promedio_estrellas": promedio,
            "total_calificaciones": len(calificaciones),
            "calificaciones": [
                {
                    "id": c.id,
                    "trueque_id": c.trueque_id,
                    "usuario_califica_id": c.usuario_califica_id,
                    "estrellas": c.estrellas,
                    "resena": c.resena,
                    "fecha_calificacion": c.fecha_calificacion.isoformat() if c.fecha_calificacion else None,
                }
                for c in calificaciones
            ],
        }

    async def listar_calificaciones_usuario(self, usuario_id: int) -> List[Calificacion]:
        return await self.calificacion_repo.list_by_usuario_calificado(usuario_id)
