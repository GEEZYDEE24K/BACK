from collections.abc import AsyncGenerator
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, relationship
from backend_estudiantil.config.settings import settings

Base = declarative_base()

# Motor y fábrica de sesiones global
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

def get_engine(url: str | None = None):
    """Retorna o regenera el motor y la fábrica de sesiones si cambió la URL."""
    global engine, AsyncSessionLocal
    target_url = url or settings.DATABASE_URL
    if str(engine.url) != target_url:
        engine = create_async_engine(target_url, echo=False, future=True)
        AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine

def get_session_factory():
    """Retorna la fábrica de sesiones activa correspondiente al motor actual."""
    get_engine()
    return AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Generador de sesión de base de datos para inyección de dependencias en FastAPI."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def verificar_conexion_db() -> dict:
    """Verifica si la conexión activa a la base de datos responde exitosamente."""
    try:
        active_engine = get_engine()
        async with active_engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
        return {
            "status": "conectado",
            "dialecto": active_engine.dialect.name,
            "url": f"{active_engine.url.drivername}://{active_engine.url.host or 'localhost'}/{active_engine.url.database or ''}",
        }
    except Exception as exc:
        return {"status": "error", "detalle": str(exc)}

# ==============================================================================
# MODELOS ORM DE LA PLATAFORMA DE TRUEQUE ESTUDIANTIL (EN ESPAÑOL)
tipo_usuario_enum = sa.Enum("estudiante", "docente", "administrativo", name="tipo_usuario_enum", create_type=False)
rol_enum = sa.Enum("usuario", "administrador", "moderador", name="rol_enum", create_type=False)
estado_cuenta_enum = sa.Enum("pendiente", "activo", "bloqueado", name="estado_cuenta_enum", create_type=False)
estado_publicacion_enum = sa.Enum("activa", "inactiva", "eliminada", name="estado_publicacion_enum", create_type=False)
tipo_match_enum = sa.Enum("exacta", "similar", name="tipo_match_enum", create_type=False)
estado_trueque_enum = sa.Enum("propuesto", "confirmado", "rechazado", "completado", name="estado_trueque_enum", create_type=False)

class UserORM(Base):
    """Tabla 'usuarios' en PostgreSQL."""
    __tablename__ = "usuarios"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True, index=True)
    nombre = sa.Column(sa.String, nullable=False)
    apellido = sa.Column(sa.String, nullable=True)
    correo_institucional = sa.Column(sa.String, unique=True, nullable=False, index=True)
    password_hash = sa.Column(sa.String, nullable=False)
    tipo_usuario = sa.Column(tipo_usuario_enum, default="estudiante", nullable=False)
    programa_area = sa.Column(sa.String, nullable=True)
    rol = sa.Column(rol_enum, default="usuario", nullable=False)
    verificado_comunidad = sa.Column(sa.Boolean, default=True, nullable=False)
    estado_cuenta = sa.Column(estado_cuenta_enum, default="activo", nullable=False)
    fecha_registro = sa.Column(sa.DateTime, default=sa.func.now(), nullable=False)

    # Relaciones
    publicaciones = relationship("PublicacionORM", back_populates="usuario", cascade="all, delete-orphan", foreign_keys="PublicacionORM.usuario_id")


class CategoriaORM(Base):
    """Tabla 'categorias' de libros y materiales académicos."""
    __tablename__ = "categorias"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    nombre = sa.Column(sa.String, nullable=False, unique=True)

    publicaciones = relationship("PublicacionORM", back_populates="categoria")


class PublicacionORM(Base):
    """Tabla 'publicaciones' de artículos ofertados y buscados."""
    __tablename__ = "publicaciones"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True, index=True)
    usuario_id = sa.Column(sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False, index=True)
    titulo = sa.Column(sa.String, nullable=False, index=True)
    autor = sa.Column(sa.String, nullable=True)
    isbn = sa.Column(sa.String, nullable=True)
    edicion = sa.Column(sa.String, nullable=True)
    categoria_id = sa.Column(sa.Integer, sa.ForeignKey("categorias.id"), nullable=True)
    estado_libro = sa.Column(sa.String, nullable=True)
    descripcion = sa.Column(sa.Text, nullable=True)
    libro_buscado = sa.Column(sa.String, nullable=True, index=True)
    estado_publicacion = sa.Column(estado_publicacion_enum, default="activa", nullable=False)
    fecha_publicacion = sa.Column(sa.DateTime, default=sa.func.now(), nullable=False)

    # Relaciones
    usuario = relationship("UserORM", back_populates="publicaciones", foreign_keys=[usuario_id])
    categoria = relationship("CategoriaORM", back_populates="publicaciones")


class VerificacionPublicacionORM(Base):
    """Desafío visual y evidencia privada para revisar una publicación de libro."""

    __tablename__ = "verificaciones_publicacion"
    __table_args__ = (
        sa.Index("ix_verificaciones_publicacion_estado", "estado"),
        sa.Index("ix_verificaciones_publicacion_usuario", "usuario_id"),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    publicacion_id = sa.Column(
        sa.Integer, sa.ForeignKey("publicaciones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usuario_id = sa.Column(sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False)
    codigo_hash = sa.Column(sa.String(64), nullable=False)
    estado = sa.Column(sa.String(24), nullable=False, default="desafio")
    intentos_codigo = sa.Column(sa.SmallInteger, nullable=False, default=0)
    portada_path = sa.Column(sa.String(512), nullable=True)
    pagina_isbn_path = sa.Column(sa.String(512), nullable=True)
    portada_sha256 = sa.Column(sa.String(64), nullable=True)
    pagina_isbn_sha256 = sa.Column(sa.String(64), nullable=True)
    creado_en = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    vence_en = sa.Column(sa.DateTime(timezone=True), nullable=False)
    enviado_en = sa.Column(sa.DateTime(timezone=True), nullable=True)
    revisado_por_id = sa.Column(sa.Integer, sa.ForeignKey("usuarios.id"), nullable=True)
    revisado_en = sa.Column(sa.DateTime(timezone=True), nullable=True)
    nota_revision = sa.Column(sa.String(1000), nullable=True)


class MatchORM(Base):
    """Tabla 'matches' generados por el motor de coincidencias."""
    __tablename__ = "matches"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True, index=True)
    publicacion_origen_id = sa.Column(sa.Integer, sa.ForeignKey("publicaciones.id"), nullable=False)
    publicacion_destino_id = sa.Column(sa.Integer, sa.ForeignKey("publicaciones.id"), nullable=False)
    tipo_match = sa.Column(tipo_match_enum, default="exacta", nullable=False)
    puntuacion = sa.Column(sa.Numeric(5, 2), default=100.0, nullable=False)
    fecha_creacion = sa.Column(sa.DateTime, default=sa.func.now(), nullable=False)

    # Relaciones
    publicacion_origen = relationship("PublicacionORM", foreign_keys=[publicacion_origen_id])
    publicacion_destino = relationship("PublicacionORM", foreign_keys=[publicacion_destino_id])


class TruequeORM(Base):
    """Tabla 'trueques' que representa el estado del intercambio entre dos usuarios."""
    __tablename__ = "trueques"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True, index=True)
    match_id = sa.Column(sa.Integer, sa.ForeignKey("matches.id"), nullable=True)
    usuario_propone_id = sa.Column(sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False)
    usuario_recibe_id = sa.Column(sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False)
    estado = sa.Column(estado_trueque_enum, default="propuesto", nullable=False)
    fecha_propuesta = sa.Column(sa.DateTime, default=sa.func.now(), nullable=False)
    fecha_confirmacion = sa.Column(sa.DateTime, nullable=True)
    fecha_completado = sa.Column(sa.DateTime, nullable=True)

    # Relaciones
    usuario_propone = relationship("UserORM", foreign_keys=[usuario_propone_id])
    usuario_recibe = relationship("UserORM", foreign_keys=[usuario_recibe_id])
    match = relationship("MatchORM")
    calificaciones = relationship("CalificacionORM", back_populates="trueque")


class CalificacionORM(Base):
    """Tabla 'calificaciones' post-trueque para calcular reputación."""
    __tablename__ = "calificaciones"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True, index=True)
    trueque_id = sa.Column(sa.Integer, sa.ForeignKey("trueques.id"), nullable=False)
    usuario_califica_id = sa.Column(sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False)
    usuario_calificado_id = sa.Column(sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False)
    estrellas = sa.Column(sa.SmallInteger, nullable=False)
    resena = sa.Column(sa.Text, nullable=True)
    fecha_calificacion = sa.Column(sa.DateTime, default=sa.func.now(), nullable=False)

    # Relaciones
    trueque = relationship("TruequeORM", back_populates="calificaciones")
    usuario_califica = relationship("UserORM", foreign_keys=[usuario_califica_id])
    usuario_calificado = relationship("UserORM", foreign_keys=[usuario_calificado_id])


class MensajeORM(Base):
    """Tabla 'mensajes' de chat asociado al intercambio/trueque."""
    __tablename__ = "mensajes"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True, index=True)
    trueque_id = sa.Column(sa.Integer, sa.ForeignKey("trueques.id"), nullable=False, index=True)
    remitente_id = sa.Column(sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False)
    contenido = sa.Column(sa.Text, nullable=False)
    fecha_envio = sa.Column(sa.DateTime, default=sa.func.now(), nullable=False)

    trueque = relationship("TruequeORM")
    remitente = relationship("UserORM", foreign_keys=[remitente_id])
