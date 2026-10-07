from datetime import datetime, timezone
from typing import Optional

class User:
    """Entidad de dominio que representa a un usuario / estudiante en la plataforma de trueque."""

    def __init__(
        self,
        id: Optional[int] = None,
        nombre: str = "",
        apellido: Optional[str] = None,
        correo_institucional: str = "",
        password_hash: str = "",
        tipo_usuario: str = "estudiante",
        programa_area: Optional[str] = None,
        rol: str = "usuario",
        verificado_comunidad: bool = True,
        estado_cuenta: str = "activo",
        fecha_registro: Optional[datetime] = None,
        # Argumentos compatibles con llamadas anteriores
        email: Optional[str] = None,
        hashed_password: Optional[str] = None,
        name: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        carrera: Optional[str] = None,
        telefono: Optional[str] = None,
        universidad: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.correo_institucional = correo_institucional or email or ""
        self.password_hash = password_hash or hashed_password or ""
        
        # Mapeo de nombre
        if name and not nombre:
            partes = name.split(" ", 1)
            self.nombre = partes[0]
            self.apellido = partes[1] if len(partes) > 1 else (apellido or "")
        else:
            self.nombre = nombre
            self.apellido = apellido or ""

        self.tipo_usuario = tipo_usuario
        self.programa_area = programa_area or carrera
        self.rol = rol if rol != "usuario" else (role or "usuario")
        self.verificado_comunidad = verificado_comunidad
        self.estado_cuenta = estado_cuenta if is_active is None else ("activo" if is_active else "bloqueado")
        self.fecha_registro = fecha_registro or created_at or datetime.now(timezone.utc)
        self.telefono = telefono
        self.universidad = universidad

    # Propiedades de compatibilidad
    @property
    def email(self) -> str:
        return self.correo_institucional

    @email.setter
    def email(self, value: str):
        self.correo_institucional = value

    @property
    def name(self) -> str:
        return f"{self.nombre} {self.apellido}".strip() if self.apellido else self.nombre

    @name.setter
    def name(self, value: str):
        partes = (value or "").split(" ", 1)
        self.nombre = partes[0]
        self.apellido = partes[1] if len(partes) > 1 else ""

    @property
    def hashed_password(self) -> str:
        return self.password_hash

    @hashed_password.setter
    def hashed_password(self, value: str):
        self.password_hash = value

    @property
    def role(self) -> str:
        return self.rol

    @role.setter
    def role(self, value: str):
        self.rol = value

    @property
    def is_active(self) -> bool:
        return self.estado_cuenta == "activo"

    @is_active.setter
    def is_active(self, value: bool):
        self.estado_cuenta = "activo" if value else "bloqueado"

    @property
    def carrera(self) -> Optional[str]:
        return self.programa_area

    @carrera.setter
    def carrera(self, value: Optional[str]):
        self.programa_area = value

    @property
    def created_at(self) -> datetime:
        return self.fecha_registro

    @property
    def updated_at(self) -> datetime:
        return self.fecha_registro
