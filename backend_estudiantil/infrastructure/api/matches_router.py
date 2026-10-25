from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from backend_estudiantil.adapters.db.sqlalchemy_match_repository import SQLAlchemyMatchRepository
from backend_estudiantil.adapters.db.sqlalchemy_publicacion_repository import SQLAlchemyPublicacionRepository
from backend_estudiantil.domain.services.match_service import MatchService
from backend_estudiantil.infrastructure.security import get_current_user
from backend_estudiantil.schemas.trueque import MatchRead

router = APIRouter(prefix="/matches", tags=["matches"])


def get_match_service() -> MatchService:
    return MatchService(
        match_repo=SQLAlchemyMatchRepository(),
        publicacion_repo=SQLAlchemyPublicacionRepository(),
    )


def _match_to_read(m) -> MatchRead:
    return MatchRead(
        id=m.id,
        publicacion_origen_id=m.publicacion_origen_id,
        publicacion_destino_id=m.publicacion_destino_id,
        tipo_match=m.tipo_match,
        puntuacion=m.puntuacion,
        fecha_creacion=m.fecha_creacion,
    )


@router.get("/mis-matches", response_model=List[MatchRead], summary="Mis coincidencias")
async def mis_matches(
    current_user: dict = Depends(get_current_user),
    service: MatchService = Depends(get_match_service),
):
    """Retorna todos los matches (coincidencias) del usuario autenticado."""
    matches = await service.listar_matches_usuario(current_user["id"])
    return [_match_to_read(m) for m in matches]


@router.get("/{match_id}", response_model=MatchRead, summary="Detalle de match")
async def obtener_match(
    match_id: int,
    current_user: dict = Depends(get_current_user),
    service: MatchService = Depends(get_match_service),
):
    """Retorna el detalle de un match por su ID."""
    try:
        match = await service.obtener_match(match_id)
        return _match_to_read(match)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/buscar/{publicacion_id}", response_model=List[MatchRead], summary="Buscar matches para publicación")
async def buscar_matches(
    publicacion_id: int,
    current_user: dict = Depends(get_current_user),
    service: MatchService = Depends(get_match_service),
):
    """
    Ejecuta el motor de matching para una publicación específica.
    Busca publicaciones complementarias y registra los matches encontrados.
    """
    try:
        matches = await service.buscar_matches_para_publicacion(publicacion_id)
        return [_match_to_read(m) for m in matches]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
