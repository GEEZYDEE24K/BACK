from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Logging configuration
from backend_estudiantil.infrastructure.logging import configure_logging
configure_logging()

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["100/min"])

# Metrics
from prometheus_fastapi_instrumentator import Instrumentator

# Routers
from backend_estudiantil.infrastructure.api.auth_router import router as auth_router
from backend_estudiantil.infrastructure.api.users_router import router as users_router
from backend_estudiantil.infrastructure.api.admin_router import router as admin_router
from backend_estudiantil.infrastructure.api.google_oauth_router import router as google_oauth_router
from backend_estudiantil.infrastructure.api.publicaciones_router import router as publicaciones_router
from backend_estudiantil.infrastructure.api.matches_router import router as matches_router
from backend_estudiantil.infrastructure.api.trueques_router import router as trueques_router
from backend_estudiantil.infrastructure.api.calificaciones_router import router as calificaciones_router
from backend_estudiantil.infrastructure.api.chat_router import router as chat_router
from backend_estudiantil.infrastructure.api.verificaciones_router import router as verificaciones_router

import os
from fastapi.staticfiles import StaticFiles

from backend_estudiantil.adapters.db import (
    Base,
    CategoriaORM,
    get_engine,
    get_session_factory,
    verificar_conexion_db,
)
from sqlalchemy import select, text

CATEGORIAS_INICIALES = (
    (1, "Ingeniería y Tecnología"),
    (2, "Medicina y Salud"),
    (3, "Ciencias Básicas"),
    (4, "Derecho y Políticas"),
    (5, "Economía y Negocios"),
    (6, "Humanidades"),
)


async def inicializar_categorias():
    factory = get_session_factory()
    async with factory() as session:
        for categoria_id, nombre in CATEGORIAS_INICIALES:
            categoria = await session.get(CategoriaORM, categoria_id)
            if categoria is None:
                existente = await session.execute(
                    select(CategoriaORM).where(CategoriaORM.nombre == nombre)
                )
                if existente.scalar_one_or_none() is None:
                    session.add(CategoriaORM(id=categoria_id, nombre=nombre))
        await session.commit()

    if get_engine().dialect.name == "postgresql":
        async with get_engine().begin() as connection:
            await connection.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('categorias', 'id'), "
                    "COALESCE((SELECT MAX(id) FROM categorias), 1))"
                )
            )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestor de ciclo de vida moderno de FastAPI (Lifespan)."""
    import asyncio
    # Inicialización de tablas en la base de datos
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await inicializar_categorias()
    yield
    # Limpieza o cierre de conexiones si es necesario al apagar el servidor

app = FastAPI(
    title="Plataforma de Trueque Estudiantil",
    description="API Backend para intercambio de artículos y libros entre estudiantes universitarios.",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Manejador de error para Rate Limit
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

from backend_estudiantil.infrastructure.api.facebook_oauth_router import router as facebook_oauth_router

# Inclusión de Routers (Auth, Usuarios, Admin, Google OAuth)
app.include_router(auth_router)
app.include_router(google_oauth_router)
app.include_router(facebook_oauth_router)
app.include_router(users_router)
app.include_router(admin_router)
# Routers del dominio principal de trueque
app.include_router(publicaciones_router)
app.include_router(matches_router)
app.include_router(trueques_router)
app.include_router(calificaciones_router)
app.include_router(chat_router)
app.include_router(verificaciones_router)

# Instrumentación de métricas con Prometheus
Instrumentator().instrument(app).expose(app)

# Health checks
@app.get("/health", tags=["health"])
async def health_check():
    """Verificación básica de salud de la API."""
    return {"status": "ok", "app": "Plataforma de Trueque Estudiantil"}

@app.get("/health/db", tags=["health"])
async def health_db_check():
    """Verificación directa de la conexión activa a la base de datos."""
    resultado = await verificar_conexion_db()
    return {"database": resultado}

# Montaje de frontend estático si existe
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
