# README

## Plataforma de Trueque Estudiantil – Backend

Este repositorio contiene el **backend** implementado con **FastAPI**, **SQLAlchemy Async**, **PostgreSQL** y una arquitectura **hexagonal**.  Incluye:

- CRUD de usuarios
- Registro / login con JWT y refresh‑token en cookie segura
- Configuración vía variables de entorno (`.env`)
- Dockerfile listo para producción (sin entorno virtual)
- Tests unitarios e integración con `pytest` y `httpx`
- Herramientas de linting/formatting (`ruff`, `black`)

### Requisitos
- Python 3.12 o superior
- PostgreSQL (para entorno real) – la URL se define en `DATABASE_URL`
- Docker (opcional, para despliegue en contenedor)

### Instalación (sin venv)
```bash
# Clonar o copiar el proyecto
cd backendEstudiantil

# Instalar dependencias globalmente
pip install -r backend_estudiantil/requirements.txt

# Copiar y editar variables de entorno
cp backend_estudiantil/.env.example backend_estudiantil/.env
# Edita .env con tus credenciales de base de datos y secret JWT
```

### Ejecutar la API
```bash
uvicorn backend_estudiantil.infrastructure.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Swagger**: <http://localhost:8000/docs>
- **Health‑check**: <http://localhost:8000/health>

### Tests
```bash
pytest backend_estudiantil/tests
```

### Docker
```bash
# Construir la imagen
docker build -t trueque-backend .
# Levantar con Docker Compose (incluye PostgreSQL 15)
docker compose up --build
```

---
**Autor**: Equipo de desarrollo de Trueque Estudiantil
