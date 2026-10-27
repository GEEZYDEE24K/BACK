import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from backend_estudiantil.config.settings import settings
from backend_estudiantil.domain.models.user import User
from backend_estudiantil.adapters.security.password_hasher import hash_password, verify_password
from backend_estudiantil.ports.repositories.user_repository import UserRepository
from backend_estudiantil.ports.notifications.email_sender import EmailSender
from backend_estudiantil.adapters.notifications.email_sender import SMTPEmailSender
from backend_estudiantil.schemas.user import UserCreate, UserUpdate

class UserService:
    """Servicio de dominio para la lógica de negocio de usuarios y estudiantes."""

    def __init__(self, repo: UserRepository, email_sender: Optional[EmailSender] = None):
        self.repo = repo
        self.email_sender = email_sender or SMTPEmailSender()

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

        # Regla: NO marcar verificado_comunidad=True solo por el dominio en registro con contraseña.
        # Si el correo es de dominio institucional, se envía código de confirmación.
        es_inst = settings.es_dominio_institucional(payload.email)
        universidad = settings.obtener_universidad_por_dominio(payload.email) if es_inst else getattr(payload, "universidad", None)
        carrera = getattr(payload, "carrera", None)
        nombre = payload.name or ""
        perfil_completo = bool(nombre.strip() and universidad and carrera)

        codigo_conf = None
        expira_conf = None
        if es_inst:
            codigo_conf = f"{secrets.randbelow(900000) + 100000}"
            expira_conf = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)

        user = User(
            correo_institucional=payload.email,
            password_hash=hashed,
            name=payload.name,
            rol="administrador" if (payload.role or "").lower() in ("admin", "administrador") else "usuario",
            estado_cuenta="activo",
            verificado_comunidad=False,  # Inicia False hasta que se confirme el código/enlace
            programa_area=carrera,
            universidad=universidad,
            telefono=getattr(payload, "telefono", None),
            semestre=getattr(payload, "semestre", None),
            foto_url=getattr(payload, "foto_url", None),
            perfil_completo=perfil_completo,
            codigo_confirmacion=codigo_conf,
            codigo_confirmacion_expira=expira_conf,
        )
        created_user = await self.repo.create(user)

        # Enviar código o enlace de confirmación al correo institucional
        if es_inst and codigo_conf:
            enlace = f"{settings.APP_BASE_URL}/auth/confirmar-correo?email={payload.email}&codigo={codigo_conf}"
            try:
                await self.email_sender.send_verification_code(payload.email, codigo_conf, enlace)
            except Exception:
                pass

        return created_user

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

    async def confirmar_codigo_verificacion(self, email: str, codigo: str) -> User:
        """Confirma el código de verificación del correo institucional y activa verificado_comunidad."""
        user = await self.repo.get_by_email(email)
        if not user:
            raise ValueError("Usuario no encontrado")

        if user.verificado_comunidad:
            return user

        if not user.codigo_confirmacion:
            raise ValueError("No hay un proceso de verificación activo para este correo")

        if user.codigo_confirmacion.strip() != codigo.strip():
            raise ValueError("Código de confirmación incorrecto")

        if user.codigo_confirmacion_expira:
            expira = user.codigo_confirmacion_expira
            if expira.tzinfo is not None:
                expira = expira.replace(tzinfo=None)
            ahora = datetime.now(timezone.utc).replace(tzinfo=None)
            if ahora > expira:
                raise ValueError("El código de confirmación ha expirado. Solicita un nuevo código")

        # Activar verificación de comunidad
        user.verificado_comunidad = True
        if not user.universidad:
            user.universidad = settings.obtener_universidad_por_dominio(user.correo_institucional)
        user.codigo_confirmacion = None
        user.codigo_confirmacion_expira = None
        user.perfil_completo = bool(user.name and user.universidad and user.programa_area)
        return await self.repo.update(user)

    async def reenviar_codigo_verificacion(self, email: str) -> User:
        """Genera y reenvía un nuevo código de confirmación al correo institucional."""
        user = await self.repo.get_by_email(email)
        if not user:
            raise ValueError("Usuario no encontrado")

        if user.verificado_comunidad:
            raise ValueError("El correo institucional ya se encuentra verificado")

        if not settings.es_dominio_institucional(email):
            raise ValueError("Este correo no pertenece a un dominio institucional")

        nuevo_codigo = f"{secrets.randbelow(900000) + 100000}"
        user.codigo_confirmacion = nuevo_codigo
        user.codigo_confirmacion_expira = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
        updated_user = await self.repo.update(user)

        enlace = f"{settings.APP_BASE_URL}/auth/confirmar-correo?email={email}&codigo={nuevo_codigo}"
        try:
            await self.email_sender.send_verification_code(email, nuevo_codigo, enlace)
        except Exception:
            pass

        return updated_user

