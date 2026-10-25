"""
moderacion_contenido_service.py
-------------------------------
Servicio de dominio para la detección, filtrado y moderación de vocabulario
inadecuado y términos prohibidos en español (con modismos y jerga de Colombia).

Severidades:
  - leve   : enmascara la palabra ofensiva (ej. "mierda" -> "m****a") y permite continuar.
  - media  : advierte y rechaza la acción ("ADVERTENCIA_APLICADA").
  - grave  : bloquea totalmente la acción ("SANCION_APLICADA" / "INFRACCION_CONTENIDO_PROHIBIDO").

Normalización de texto:
  - Eliminación de acentos y tildes (á->a, é->e, etc.).
  - Conversión a minúsculas.
  - Normalización de leetspeak (@/4->a, 3->e, 1/!/|->i, 0->o, 5/$->s, 7->t, 8->b).
  - Colapso de letras repetidas (ej. "gonorrrrea" -> "gonorrea").
  - Detección de caracteres separadores entre letras (ej. "h.p.t.a").
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional, List, Tuple


@dataclass
class ResultadoModeracion:
    """Resultado del análisis de moderación de contenido."""
    es_valido: bool
    texto_final: str
    nivel_severidad: Optional[str] = None  # None, "leve", "media", "grave"
    accion: Optional[str] = None           # None, "enmascarar", "advertir", "bloquear"
    terminos_detectados: List[str] = field(default_factory=list)
    accion_auditoria: Optional[str] = None # INFRACCION_VOCABULARIO, ADVERTENCIA_APLICADA, SANCION_APLICADA
    mensaje_error: Optional[str] = None


class ModeracionContenidoService:
    """Servicio de dominio hexagonal para filtrado y moderación de contenidos."""

    # Términos leves en español / Colombia -> Enmascarar
    TERMINOS_LEVES = [
        "mierda", "estupido", "estupida", "pendejo", "pendeja",
        "guevon", "guevona", "huevon", "huevona", "idiota",
        "bobo", "boba", "tarado", "tarada", "baboso", "babosa",
        "culillo", "culicagado", "culicagada", "pingo",
    ]

    # Términos medios en español / Colombia -> Advertir y rechazar
    TERMINOS_MEDIOS = [
        "gonorrea", "malparido", "malparida", "carechimba", "pirobo", "piroba",
        "careverga", "hijo de puta", "hija de puta", "hpta", "hijueputa", "hp",
        "culiao", "sapo hijueputa", "guiso", "guisa", "marica", "perra", "zorra",
        "chucha", "careculo",
    ]

    # Términos graves -> Bloquear y reportar sanción/infracción grave
    TERMINOS_GRAVES = [
        "sicario", "traqueto", "cocaina", "bazuco", "te voy a matar",
        "amenaza de muerte", "secuestro", "fleteo", "gota a gota",
        "pornografia", "violacion", "armas de fuego", "traficante",
        "narcotrafico", "marihuana", "estupefaciente",
    ]

    # Mapeo de leetspeak
    LEET_MAP = {
        "@": "a", "4": "a",
        "3": "e",
        "1": "i", "!": "i", "|": "i",
        "0": "o",
        "5": "s", "$": "s",
        "7": "t",
        "8": "b",
    }

    @classmethod
    def normalizar(cls, texto: str) -> str:
        """Normaliza un texto removiendo tildes, leetspeak, caracteres repetidos y separadores."""
        if not texto:
            return ""

        # 1. Minúsculas
        t = texto.lower()

        # 2. Descomponer tildes y diacríticos
        t = unicodedata.normalize("NFKD", t)
        t = "".join(c for c in t if not unicodedata.combining(c))

        # 3. Mapear leetspeak
        for leet, char in cls.LEET_MAP.items():
            t = t.replace(leet, char)

        # 4. Colapsar repetición de letras (ej. "hptaaaa" -> "hpta", "gonorrrrea" -> "gonorrea")
        t = re.sub(r"(.)\1{2,}", r"\1", t)

        return t

    @classmethod
    def _enmascarar_palabra(cls, palabra: str) -> str:
        """Enmascara una palabra leve con asteriscos manteniendo la primera y última letra."""
        if len(palabra) <= 2:
            return "*" * len(palabra)
        return palabra[0] + ("*" * (len(palabra) - 2)) + palabra[-1]

    def procesar_texto(self, texto: str) -> ResultadoModeracion:
        """
        Analiza el texto y retorna el resultado de moderación según severidad:
          - Grave : bloquea
          - Media : advierte
          - Leve  : enmascara y aprueba
        """
        if not texto or not texto.strip():
            return ResultadoModeracion(es_valido=True, texto_final=texto or "")

        norm = self.normalizar(texto)
        # Variante compacta sin espacios ni puntuación para detectar "h.p.t.a" o "g o n o r r e a"
        compact = re.sub(r"[\s\.\-_,;:]+", "", norm)

        # 1. Comprobar GRAVES
        detectados_graves = []
        for termino in self.TERMINOS_GRAVES:
            norm_term = self.normalizar(termino)
            patron = rf"\b{re.escape(norm_term)}\b"
            if re.search(patron, norm) or (len(norm_term) >= 5 and norm_term in compact):
                detectados_graves.append(termino)

        if detectados_graves:
            return ResultadoModeracion(
                es_valido=False,
                texto_final=texto,
                nivel_severidad="grave",
                accion="bloquear",
                terminos_detectados=detectados_graves,
                accion_auditoria="SANCION_APLICADA",
                mensaje_error="Operación bloqueada por contenido o vocabulario grave prohibido.",
            )

        # 2. Comprobar MEDIOS (Advertir y rechazar)
        detectados_medios = []
        for termino in self.TERMINOS_MEDIOS:
            norm_term = self.normalizar(termino)
            patron = rf"\b{re.escape(norm_term)}\b"
            if re.search(patron, norm) or (len(norm_term) >= 4 and norm_term in compact):
                detectados_medios.append(termino)

        if detectados_medios:
            return ResultadoModeracion(
                es_valido=False,
                texto_final=texto,
                nivel_severidad="media",
                accion="advertir",
                terminos_detectados=detectados_medios,
                accion_auditoria="ADVERTENCIA_APLICADA",
                mensaje_error="Mensaje rechazado por vocabulario inadecuado (advertencia). Modere su lenguaje.",
            )

        # 3. Comprobar LEVES (Enmascarar y permitir)
        texto_enmascarado = texto
        detectados_leves = []
        for termino in self.TERMINOS_LEVES:
            norm_term = self.normalizar(termino)
            patron = rf"\b{re.escape(norm_term)}\b"
            # Buscar en el texto original preservando mayúsculas/minúsculas
            coincidencias = list(re.finditer(rf"\b{re.escape(termino)}\b", texto_enmascarado, re.IGNORECASE))
            if not coincidencias:
                # Buscar con forma normalizada
                if re.search(patron, norm):
                    detectados_leves.append(termino)
                    # Reemplazo enmascarado
                    texto_enmascarado = re.sub(
                        rf"(?i)\b{re.escape(termino)}\b",
                        self._enmascarar_palabra(termino),
                        texto_enmascarado
                    )
            else:
                detectados_leves.append(termino)
                for m in reversed(coincidencias):
                    original_word = m.group(0)
                    masked = self._enmascarar_palabra(original_word)
                    texto_enmascarado = texto_enmascarado[:m.start()] + masked + texto_enmascarado[m.end():]

        if detectados_leves:
            return ResultadoModeracion(
                es_valido=True,
                texto_final=texto_enmascarado,
                nivel_severidad="leve",
                accion="enmascarar",
                terminos_detectados=detectados_leves,
                accion_auditoria="INFRACCION_VOCABULARIO",
                mensaje_error=None,
            )

        return ResultadoModeracion(
            es_valido=True,
            texto_final=texto,
            nivel_severidad=None,
            accion=None,
            terminos_detectados=[],
            accion_auditoria=None,
            mensaje_error=None,
        )
