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

from backend_estudiantil.adapters.db import Base, get_engine, verificar_conexion_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestor de ciclo de vida moderno de FastAPI (Lifespan)."""
    # Inicialización de tablas en la base de datos
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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

# Inclusión de Routers (Auth, Usuarios, Admin, Google OAuth)
app.include_router(auth_router)
app.include_router(google_oauth_router)
app.include_router(users_router)
app.include_router(admin_router)
# Routers del dominio principal de trueque
app.include_router(publicaciones_router)
app.include_router(matches_router)
app.include_router(trueques_router)
app.include_router(calificaciones_router)

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
