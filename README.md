# Plataforma de Trueque Estudiantil – Backend

Este repositorio contiene la API backend de la **Plataforma de Trueque Estudiantil**, desarrollada con **FastAPI**, **SQLAlchemy Async**, **PostgreSQL** (con soporte para SQLite local) bajo una **Arquitectura Hexagonal**.

Permite el registro e inicio de sesión de estudiantes universitarios, gestión de perfiles, autenticación robusta mediante tokens JWT y refresh tokens en cookies HttpOnly seguras, y hashing criptográfico con **bcrypt**.

---

## 🛠️ Características Principales

- **Arquitectura Hexagonal**: Separación limpia entre Dominio, Puertos, Adaptadores e Infraestructura.
- **Base de Datos Visible y Flexible**: Configuración directa mediante la variable de entorno `DATABASE_URL` (PostgreSQL asíncrono vía `asyncpg` o SQLite vía `aiosqlite`).
- **Nomenclatura en Español**: Tabla `usuarios` con campos académicos y de contacto (`carrera`, `universidad`, `telefono`, `is_active`, `created_at`, `updated_at`).
- **Autenticación y Seguridad**:
  - Hashing seguro de contraseñas con **bcrypt**.
  - Emisión de **Access Token JWT** con identificador único RFC 7519 (`jti`).
  - **Refresh Token** almacenado en cookies `HttpOnly` y `SameSite`.
  - Endpoint para cierre seguro de sesión (`/auth/logout`).
  - Soporte integrado para **Google OAuth2**.
- **Gestión de Perfiles y Usuarios**:
  - `GET /usuarios/me` y `PUT /usuarios/me` para consulta y edición de perfil propio.
  - CRUD administrativo con control de roles (`admin`, `moderador`, `user`).
  - Endpoint para verificación de salud de la base de datos (`GET /health/db`).
- **Migraciones con Alembic**: Migración en español `1975ea83b712_crear_tabla_usuarios.py`.
- **Suite de Pruebas Automatizadas**: 100% en verde con `pytest` y `httpx`.

---

## 📋 Requisitos

- Python 3.12 o superior
- PostgreSQL 14+ (o SQLite local para pruebas rápidas)
- Docker y Docker Compose (opcional)

---

## 🚀 Instalación y Puesta en Marcha

### 1. Clonar el repositorio y configurar variables de entorno
```bash
# Copiar archivo de variables de entorno
cp backend_estudiantil/.env.example .env
```

Edita `.env` con la cadena de conexión de tu base de datos:
```env
# Conexión a PostgreSQL:
DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5432/trueque

# O si deseas usar SQLite local para desarrollo sin levantar Postgres:
# DATABASE_URL=sqlite+aiosqlite:///./trueque_estudiantil.db

COOKIE_SECURE=False
JWT_SECRET_KEY=MySuperSecretKey1234567890!@#$%^&*()_+
```

### 2. Instalar dependencias
```bash
pip install -r backend_estudiantil/requirements.txt
```

### 3. Ejecutar la API
```bash
uvicorn backend_estudiantil.infrastructure.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📖 Documentación Interactiva

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>
- **Health Check General**: <http://localhost:8000/health>
- **Health Check Base de Datos**: <http://localhost:8000/health/db>

---

## 📌 Catálogo de Endpoints

### 🔐 Autenticación (`/auth`)
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/auth/register` | Registro de nuevo estudiante |
| `POST` | `/auth/login` | Login con credenciales (emite JWT y cookie HttpOnly) |
| `POST` | `/auth/refresh` | Renovación de Access Token mediante cookie |
| `POST` | `/auth/logout` | Cierre de sesión y revocación de cookie |
| `GET` | `/auth/google/login` | URL para inicio de sesión federado con Google |
| `GET` | `/auth/google/callback` | Callback de Google OAuth2 |

### 👤 Usuarios y Perfiles (`/usuarios`)
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/usuarios/me` | Consulta del perfil del estudiante autenticado |
| `PUT` | `/usuarios/me` | Actualización de perfil propio (nombre, carrera, teléfono) |
| `GET` | `/usuarios/` | Listado paginado de usuarios (requiere autenticación) |
| `GET` | `/usuarios/{user_id}` | Detalle de un usuario específico |
| `POST` | `/usuarios/` | Creación de usuario (rol admin) |
| `PUT` | `/usuarios/{user_id}` | Actualización de usuario (propio o admin) |
| `DELETE` | `/usuarios/{user_id}` | Eliminación de usuario (rol admin) |

### 🛡️ Administración (`/admin`)
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/admin/users/{user_id}/promote` | Promover usuario a rol moderador |

---

## 🧪 Ejecución de Pruebas Automatizadas

Para ejecutar todas las pruebas unitarias y de integración:
```bash
pytest -v
```

---

## 🐳 Despliegue con Docker

```bash
docker compose up --build
```
Esto levantará el contenedor de la API en el puerto `8000` junto con una instancia de PostgreSQL en el puerto `5432`.
