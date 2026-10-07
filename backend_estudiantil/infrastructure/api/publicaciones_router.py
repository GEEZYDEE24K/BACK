from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend_estudiantil.adapters.db.sqlalchemy_publicacion_repository import SQLAlchemyPublicacionRepository
from backend_estudiantil.domain.services.publicacion_service import PublicacionService
from backend_estudiantil.infrastructure.security import get_current_user
from backend_estudiantil.schemas.publicacion import PublicacionCreate, PublicacionRead, PublicacionUpdate

router = APIRouter(prefix="/publicaciones", tags=["publicaciones"])


def get_publicacion_service() -> PublicacionService:
    return PublicacionService(SQLAlchemyPublicacionRepository())


def _pub_to_read(pub) -> PublicacionRead:
    return PublicacionRead(
        id=pub.id,
        usuario_id=pub.usuario_id,
        titulo=pub.titulo,
        autor=pub.autor,
        isbn=pub.isbn,
        edicion=pub.edicion,
        categoria_id=pub.categoria_id,
        estado_libro=pub.estado_libro,
        descripcion=pub.descripcion,
        libro_buscado=pub.libro_buscado,
        estado_publicacion=pub.estado_publicacion,
        fecha_publicacion=pub.fecha_publicacion,
    )


@router.get("/", response_model=List[PublicacionRead], summary="Listar publicaciones activas")
async def listar_publicaciones(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(20, ge=1, le=100, description="Máximo de registros a retornar"),
    categoria_id: Optional[int] = Query(None, description="Filtrar por categoría"),
    busqueda: Optional[str] = Query(None, description="Buscar por título, autor o libro buscado"),
    service: PublicacionService = Depends(get_publicacion_service),
):
    """Retorna el listado de publicaciones activas. Permite filtrar por categoría y búsqueda de texto."""
    pubs = await service.listar_publicaciones(
        skip=skip, limit=limit, categoria_id=categoria_id, busqueda=busqueda
    )
    return [_pub_to_read(p) for p in pubs]


@router.get("/mis-publicaciones", response_model=List[PublicacionRead], summary="Mis publicaciones")
async def mis_publicaciones(
    current_user: dict = Depends(get_current_user),
    service: PublicacionService = Depends(get_publicacion_service),
):
    """Retorna todas las publicaciones del usuario autenticado."""
    pubs = await service.listar_por_usuario(current_user["id"])
    return [_pub_to_read(p) for p in pubs]


@router.get("/{publicacion_id}", response_model=PublicacionRead, summary="Detalle de publicación")
async def obtener_publicacion(
    publicacion_id: int,
    service: PublicacionService = Depends(get_publicacion_service),
):
    """Retorna el detalle de una publicación por su ID."""
    try:
        pub = await service.obtener_publicacion(publicacion_id)
        return _pub_to_read(pub)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/", response_model=PublicacionRead, status_code=status.HTTP_201_CREATED, summary="Crear publicación")
async def crear_publicacion(
    payload: PublicacionCreate,
    current_user: dict = Depends(get_current_user),
    service: PublicacionService = Depends(get_publicacion_service),
):
    """Crea una nueva publicación de libro o material académico para intercambio."""
    try:
        pub = await service.crear_publicacion(
            usuario_id=current_user["id"],
            titulo=payload.titulo,
            autor=payload.autor,
            isbn=payload.isbn,
            edicion=payload.edicion,
            categoria_id=payload.categoria_id,
            estado_libro=payload.estado_libro,
            descripcion=payload.descripcion,
            libro_buscado=payload.libro_buscado,
        )
        return _pub_to_read(pub)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{publicacion_id}", response_model=PublicacionRead, summary="Actualizar publicación")
async def actualizar_publicacion(
    publicacion_id: int,
    payload: PublicacionUpdate,
    current_user: dict = Depends(get_current_user),
    service: PublicacionService = Depends(get_publicacion_service),
):
    """Actualiza los datos de una publicación. Solo el autor puede modificarla."""
    try:
        datos = payload.model_dump(exclude_none=True)
        pub = await service.actualizar_publicacion(publicacion_id, current_user["id"], datos)
        return _pub_to_read(pub)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{publicacion_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar publicación")
async def eliminar_publicacion(
    publicacion_id: int,
    current_user: dict = Depends(get_current_user),
    service: PublicacionService = Depends(get_publicacion_service),
):
    """Elimina una publicación. Solo el autor puede eliminarla."""
    try:
        await service.eliminar_publicacion(publicacion_id, current_user["id"])
        return None
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
