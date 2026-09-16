from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend_estudiantil.infrastructure.api.users_router import router as users_router
from backend_estudiantil.infrastructure.api.auth_router import router as auth_router
from backend_estudiantil.adapters.db import engine, Base

app = FastAPI(title="Plataforma de Trueque Estudiantil", version="0.1.0")

# CORS configuration (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from backend_estudiantil.infrastructure.api.google_oauth_router import router as google_oauth_router
app.include_router(google_oauth_router)

# Create database tables on startup
@app.on_event("startup")
async def on_startup():
    # For async engine, use run_sync to execute synchronous metadata creation
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Simple health check
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}
