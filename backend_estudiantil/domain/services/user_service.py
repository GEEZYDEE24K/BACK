from typing import List, Optional

from backend_estudiantil.config.settings import settings
from backend_estudiantil.domain.models.user import User
from backend_estudiantil.adapters.security.password_hasher import hash_password, verify_password
from backend_estudiantil.ports.repositories.user_repository import UserRepository
from backend_estudiantil.schemas.user import UserCreate, UserUpdate

class UserService:
    """Servicio de dominio para la lógica de negocio de usuarios y estudiantes."""

    def __init__(self, repo: UserRepository):
        self.repo = repo

    def _hash_password(self, password: str) -> str:
        """Genera hash seguro de contraseña (bcrypt)."""
        return hash_password(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Valida una contraseña contra su hash."""
        return verify_password(plain_password, hashed_password)

    async def create_user(self, payload: UserCreate) -> User:
        # Verificar si el correo ya existe
        existing = await self.repo.get_by_email(payload.email)
        if existing:
            raise ValueError("El correo electrónico ya está registrado")

        hashed = self._hash_password(payload.password)

        # Regla 1: Verificación de comunidad automática si el correo es institucional
        es_inst = settings.es_dominio_institucional(payload.email)
        universidad = settings.obtener_universidad_por_dominio(payload.email) if es_inst else getattr(payload, "universidad", None)
        carrera = getattr(payload, "carrera", None)
        nombre = payload.name or ""
        perfil_completo = bool(nombre.strip() and universidad and carrera)

        user = User(
            correo_institucional=payload.email,
            password_hash=hashed,
            name=payload.name,
            rol="administrador" if (payload.role or "").lower() in ("admin", "administrador") else "usuario",
            estado_cuenta="activo",
            verificado_comunidad=es_inst,
            programa_area=carrera,
            universidad=universidad,
            telefono=getattr(payload, "telefono", None),
            semestre=getattr(payload, "semestre", None),
            foto_url=getattr(payload, "foto_url", None),
            perfil_completo=perfil_completo,
        )
        return await self.repo.create(user)

    async def get_user(self, user_id: str) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.repo.get_by_email(email)

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        return await self.repo.list(skip=skip, limit=limit)

    async def update_user(self, user_id: str, payload: UserUpdate) -> User:
        user = await self.get_user(user_id)
        if payload.email and payload.email != user.correo_institucional:
            existing = await self.repo.get_by_email(payload.email)
            if existing and existing.id != user.id:
                raise ValueError("El correo electrónico ya está en uso")
            user.correo_institucional = payload.email
            if settings.es_dominio_institucional(payload.email):
                user.verificado_comunidad = True
                if not user.universidad:
                    user.universidad = settings.obtener_universidad_por_dominio(payload.email)

        if payload.name is not None:
            user.name = payload.name

        if getattr(payload, "carrera", None) is not None:
            user.programa_area = payload.carrera

        if getattr(payload, "universidad", None) is not None:
            user.universidad = payload.universidad

        if getattr(payload, "telefono", None) is not None:
            user.telefono = payload.telefono

        if getattr(payload, "semestre", None) is not None:
            user.semestre = payload.semestre

        if getattr(payload, "foto_url", None) is not None:
            user.foto_url = payload.foto_url

        if getattr(payload, "perfil_completo", None) is not None:
            user.perfil_completo = payload.perfil_completo
        else:
            # Autocalcular perfil_completo si cuenta con datos clave
            user.perfil_completo = bool(
                user.name and user.name.strip() and user.universidad and user.programa_area
            )

        if payload.password:
            user.password_hash = self._hash_password(payload.password)

        return await self.repo.update(user)

    async def promote_to_moderator(self, user_id: str) -> User:
        """Promueve al usuario a rol 'moderador'."""
        user = await self.get_user(user_id)
        user.rol = "moderador"
        return await self.repo.update(user)

    async def deactivate_user(self, user_id: str) -> User:
        """Desactiva un usuario (borrado lógico para preservar integridad de trueques y valoraciones)."""
        user = await self.get_user(user_id)
        user.estado_cuenta = "bloqueado"
        return await self.repo.update(user)

    async def delete_user(self, user_id: str) -> None:
        """Elimina un usuario por su ID."""
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        await self.repo.delete(user_id)
