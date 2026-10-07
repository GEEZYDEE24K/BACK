from typing import List, Optional

from backend_estudiantil.domain.models.match import Match
from backend_estudiantil.domain.models.publicacion import Publicacion
from backend_estudiantil.ports.repositories.match_repository import MatchRepository
from backend_estudiantil.ports.repositories.publicacion_repository import PublicacionRepository


class MatchService:
    """
    Motor de coincidencias entre publicaciones.
    Identifica y registra matches cuando hay complementariedad entre
    lo que un usuario ofrece y lo que otro busca.
    """

    def __init__(self, match_repo: MatchRepository, publicacion_repo: PublicacionRepository):
        self.match_repo = match_repo
        self.publicacion_repo = publicacion_repo

    async def buscar_matches_para_publicacion(self, publicacion_id: int) -> List[Match]:
        """
        Busca publicaciones complementarias a la dada y crea matches automáticamente.
        Lógica: si la publicacion A ofrece 'libro_X' y A.libro_buscado coincide
        con B.titulo, entonces hay un match potencial.
        """
        pub_origen = await self.publicacion_repo.get_by_id(publicacion_id)
        if not pub_origen:
            raise ValueError(f"Publicación {publicacion_id} no encontrada")

        matches_creados: List[Match] = []

        if not pub_origen.libro_buscado:
            return matches_creados  # Sin búsqueda activa, no hay matching

        # Buscar publicaciones que ofrezcan lo que esta publicación busca
        candidatas = await self.publicacion_repo.list_activas(
            busqueda=pub_origen.libro_buscado,
            limit=100,
        )

        for pub_destino in candidatas:
            # Evitar match consigo mismo
            if pub_destino.usuario_id == pub_origen.usuario_id:
                continue
            if pub_destino.id == pub_origen.id:
                continue

            # Verificar si ya existe este match
            existente = await self.match_repo.get_existing_match(pub_origen.id, pub_destino.id)
            if existente:
                continue

            # Calcular puntuación de similitud básica
            puntuacion = self._calcular_puntuacion(pub_origen, pub_destino)
            tipo = "exacta" if puntuacion >= 90.0 else "parcial"

            nuevo_match = Match(
                publicacion_origen_id=pub_origen.id,
                publicacion_destino_id=pub_destino.id,
                tipo_match=tipo,
                puntuacion=puntuacion,
            )
            match_creado = await self.match_repo.create(nuevo_match)
            matches_creados.append(match_creado)

        return matches_creados

    def _calcular_puntuacion(self, origen: Publicacion, destino: Publicacion) -> float:
        """
        Calcula una puntuación de coincidencia entre 0 y 100.
        Compara el libro buscado por origen con el título ofrecido por destino.
        """
        if not origen.libro_buscado or not destino.titulo:
            return 0.0

        buscado = origen.libro_buscado.lower().strip()
        ofrecido = destino.titulo.lower().strip()

        # Coincidencia exacta
        if buscado == ofrecido:
            return 100.0

        # Coincidencia parcial (buscado contenido en ofrecido o viceversa)
        if buscado in ofrecido or ofrecido in buscado:
            return 75.0

        # Coincidencia por palabras clave
        palabras_buscado = set(buscado.split())
        palabras_ofrecido = set(ofrecido.split())
        if palabras_buscado and palabras_ofrecido:
            comunes = palabras_buscado & palabras_ofrecido
            ratio = len(comunes) / max(len(palabras_buscado), len(palabras_ofrecido))
            if ratio > 0:
                return round(ratio * 60.0, 2)

        return 0.0

    async def obtener_match(self, match_id: int) -> Match:
        match = await self.match_repo.get_by_id(match_id)
        if not match:
            raise ValueError(f"Match {match_id} no encontrado")
        return match

    async def listar_matches_usuario(self, usuario_id: int) -> List[Match]:
        return await self.match_repo.list_by_usuario(usuario_id)
