# Plataforma de Trueque Estudiantil
## Manual Técnico y Memoria de Arquitectura Backend

**Documento Técnico Oficial de Proyecto**  
**Versión:** 1.0.0 — Backend Funcional y Documentado  
**Fecha:** Septiembre de 2026  
**Estado:** API de usuarios, publicaciones, trueques y conversaciones P2P implementada

---

### Ficha Técnica del Proyecto

| Parámetro | Valor |
|---|---|
| **Nombre del Sistema** | Plataforma de Trueque Estudiantil |
| **Componente Documentado** | Backend RESTful API (Módulo de Usuarios y Autenticación) |
| **Tecnologías Centrales** | FastAPI, SQLAlchemy 2.0 Async, PostgreSQL, Pydantic v2, PyJWT, Bcrypt |
| **Patrón Arquitectónico** | Arquitectura Hexagonal (Puertos y Adaptadores / Clean Architecture) |
| **Metodología de Trabajo** | Ágil — Scrumban (Sprints periódicos + Flujo continuo en Trello) |
| **Control de Versiones y Pruebas** | Git / GitHub · Pytest + HTTPX ASGITransport (100% verde) |
| **Persistencia** | PostgreSQL 15 (Docker/Local) + SQLite asíncrono para pruebas aisladas |

---

## 1. Introducción y Propósito del Backend

### 1.1. ¿Qué es y para qué sirve el Backend en el Sistema?
El backend es el motor computacional y lógico central de la **Plataforma de Trueque Estudiantil**. Su función consiste en gestionar y salvaguardar la información crítica del sistema, ejecutar las reglas de negocio del intercambio sin dinero, autenticar de forma segura a los estudiantes, verificar la integridad de las solicitudes mediante contratos estrictos (Pydantic v2), persistir los datos en PostgreSQL de manera asíncrona y alimentar en tiempo real a las aplicaciones clientes (web o móvil) mediante una API REST.

### 1.2. Objetivos del Negocio Universitario
- **Intercambio Solidario sin Dinero:** Facilitar el trueque de libros de texto, calculadoras científicas, apuntes académicos y batas entre compañeros de universidad.
- **Eficiencia en la Búsqueda:** Reducir a segundos el tiempo que un estudiante invierte buscando material de estudio para su semestre académico.
- **Economía Circular y Sostenibilidad:** Promover la reutilización y aprovechamiento de recursos educativos dentro del campus universitario.
- **Entorno de Confianza y Reputación:** Garantizar la tranquilidad del intercambio mediante el sistema de valoraciones con estrellas y perfiles verificados.

### 1.3. Matriz de Requerimientos del Sistema

| ID | Requerimiento | Descripción Técnica |
|---|---|---|
| **RF-01** | Registro e Inicio de Sesión | Creación de cuentas, validación de correo universitario y autenticación JWT con cookies HttpOnly. |
| **RF-02** | Gestión de Perfiles | Consulta (`/usuarios/me`) y edición de información académica: carrera, universidad y WhatsApp. |
| **RF-03** | Publicación de Ofertas | Gestión de artículos que el estudiante tiene disponibles para intercambiar. |
| **RF-04** | Publicación de Búsquedas | Declaración de materiales académicos que el estudiante necesita para su semestre. |
| **RF-05** | Motor de Matching | Algoritmo que correlaciona ofertas con búsquedas para sugerir trueques inmediatos. |
| **RF-06** | Gestión del Trueque | Control de estados de la negociación: propuesto, aceptado, completado y cancelado. |
| **RF-07** | Valoraciones Post-Trueque | Registro de calificaciones (1-5 estrellas) y comentarios tras finalizar el intercambio. |
| **RF-08** | Sistema de Reputación | Cálculo transparente de confiabilidad del estudiante visible en publicaciones. |
| **RF-09** | Validación Estricta | Sanitización y validación automática de datos con Pydantic v2 antes de persistir. |
| **RNF-01** | Seguridad Criptográfica | Hashing con bcrypt, JWT con JTI único y cookies seguras con políticas SameSite. |
| **RNF-02** | Rendimiento Asíncrono | Consultas no bloqueantes con SQLAlchemy Async y asyncpg para alta concurrencia. |

---

## 2. Arquitectura Hexagonal (Puertos y Adaptadores)

Se seleccionó una **Arquitectura Hexagonal** para desacoplar completamente la lógica de negocio del trueque de los componentes tecnológicos externos (FastAPI, PostgreSQL, PyJWT).

```mermaid
flowchart TD
    subgraph Infraestructura ["Capa de Infraestructura (FastAPI / Routers / DB)"]
        API[FastAPI Main & Routers]
        DB[(PostgreSQL / SQLite)]
    end

    subgraph Adaptadores ["Capa de Adaptadores"]
        RepoAdapt[SQLAlchemyUserRepository]
        BcryptAdapt[PasswordHasher Bcrypt]
        JWTAdapt[JWTAuthenticator]
        GoogleAdapt[GoogleOAuth2Authenticator]
    end

    subgraph Puertos ["Capa de Puertos (Interfaces ABC)"]
        UserRepoPort[UserRepository Port]
        AuthPort[Authenticator Port]
    end

    subgraph Dominio ["Capa de Dominio (Reglas Puras de Negocio)"]
        UserEntity[User Entity]
        UserService[UserService]
    end

    API --> UserService
    UserService --> UserEntity
    UserService --> UserRepoPort
    UserService --> BcryptAdapt
    UserRepoPort <|.. RepoAdapt
    AuthPort <|.. JWTAdapt
    RepoAdapt --> DB
```

### Estructura de Carpetas del Backend
```text
backend_estudiantil/
  ├── config/                  # Configuración global con Pydantic Settings (settings.py)
  ├── domain/                  # Entidades (User) y Servicios de Negocio (UserService)
  ├── ports/                   # Interfaces abstractas de repositorios y seguridad
  ├── adapters/                # Adaptadores: SQLAlchemy DB, Bcrypt Hasher, PyJWT, Google OAuth
  ├── infrastructure/          # FastAPI App, Routers (/auth, /usuarios, /admin), CORS, Logging
  ├── schemas/                 # Modelos Pydantic v2 de entrada y salida (DTOs)
  └── tests/                   # Pruebas unitarias y de integración del servicio y CRUD
alembic/                       # Control de versiones de base de datos (crear_tabla_usuarios.py)
tests/                         # Pruebas de integración de extremo a extremo (test_auth_integration.py)
.env                           # Variables de entorno con DATABASE_URL explícita
```

---

## 3. Base de Datos, Conexión y Tabla 'usuarios' en Español

### 3.1. Configuración Visible de Conexión
La conexión a la base de datos es transparente y se administra directamente mediante la variable `DATABASE_URL` en el archivo `.env`:
- **PostgreSQL (Producción / Docker):** `postgresql+asyncpg://postgres:123456@localhost:5432/trueque`
- **SQLite Asíncrono (Desarrollo local / Tests):** `sqlite+aiosqlite:///./test.db`
- **Inyección de dependencias (`get_db`):** Generador asíncrono en `adapters/db/__init__.py`.
- **Verificación de salud en vivo:** `GET /health/db` responde `{"database": {"status": "conectado", "dialecto": "postgresql", ...}}`.

### 3.2. Diccionario de Datos: Tabla 'usuarios'
| Columna | Tipo de Dato | Restricción / Clave | Descripción en el Negocio |
|---|---|---|---|
| `id` | VARCHAR (UUID) | PRIMARY KEY, INDEX | Identificador único global del estudiante. |
| `email` | VARCHAR | UNIQUE, NOT NULL, INDEX | Correo electrónico universitario (usado para login). |
| `hashed_password` | VARCHAR | NOT NULL | Hash criptográfico de la contraseña (generado con bcrypt). |
| `name` | VARCHAR | NULLABLE | Nombre y apellidos completos del estudiante. |
| `role` | VARCHAR | NOT NULL, DEFAULT 'user' | Rol de control de acceso: 'admin', 'moderador', 'user'. |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Estado de la cuenta (permite borrado lógico sin romper trueques). |
| `telefono` | VARCHAR | NULLABLE | Teléfono / WhatsApp para coordinar el intercambio físico. |
| `carrera` | VARCHAR | NULLABLE | Programa académico o carrera que cursa el estudiante. |
| `universidad` | VARCHAR | NULLABLE | Universidad o campus donde se realizan los trueques. |
| `created_at` | DATETIME | NOT NULL, SERVER DEFAULT | Fecha y hora de registro del usuario (UTC). |
| `updated_at` | DATETIME | NOT NULL, SERVER DEFAULT | Fecha y hora de la última modificación del perfil. |

---

## 4. Módulo de Autenticación y Seguridad Criptográfica

### 4.1. Hashing Seguro con Bcrypt
Implementado en `adapters/security/password_hasher.py`. Cada contraseña se cifra con un salt criptográfico aleatorio generado por `bcrypt.gensalt()`. Protege de manera efectiva contra ataques de tablas arcoíris (rainbow tables) y fuerza bruta.

### 4.2. Estrategia de Tokens JWT y JTI Único (RFC 7519)
- **Access Token:** Vida útil de 30 minutos. Contiene `sub` (ID de usuario), `role` (rol asignado), `exp` (expiración) y un identificador único `jti` (UUID4) que previene ataques de repetición y colisiones de tokens generados en el mismo segundo.
- **Refresh Token:** Vida útil de 7 días. Empleado para renovar el Access Token mediante `POST /auth/refresh`.

### 4.3. Cookies Seguras HttpOnly
El Refresh Token se almacena en una cookie del navegador con directivas de alta seguridad:
- `HttpOnly=True`: Impide el acceso desde JavaScript (mitigación de XSS).
- `SameSite=Lax`: Protección contra ataques de falsificación de peticiones (CSRF).
- `Secure=COOKIE_SECURE`: `False` en desarrollo HTTP local y `True` en producción HTTPS.
- `POST /auth/logout`: Elimina activamente la cookie de sesión en el cliente.

---

## 5. Catálogo Completo de Endpoints REST

| Método | Ruta de la API | Nivel de Acceso / Rol | Propósito Funcional |
|---|---|---|---|
| `POST` | `/auth/register` | Público | Registra un estudiante con datos académicos y emite código 201 Created. |
| `POST` | `/auth/login` | Público | Valida credenciales con bcrypt y emite Access Token + Cookie HttpOnly. |
| `POST` | `/auth/refresh` | Público (Cookie) | Renueva el Access Token a partir de la cookie de refresh token. |
| `POST` | `/auth/logout` | Autenticado | Cierra sesión y elimina la cookie de refresh token del navegador. |
| `GET` | `/auth/google/login` | Público | Genera y retorna la URL de consentimiento para Google OAuth2. |
| `GET` | `/auth/google/callback` | Público | Recibe código de Google, crea al estudiante si no existe y emite tokens. |
| `GET` | `/usuarios/me` | Estudiante (Token) | Retorna el perfil completo del usuario en sesión (carrera, WhatsApp, rol). |
| `PUT` | `/usuarios/me` | Estudiante (Token) | Actualiza nombre, teléfono de contacto o carrera del propio estudiante. |
| `GET` | `/usuarios/` | Autenticado | Listado paginado de usuarios (query params: `skip` y `limit`). |
| `GET` | `/usuarios/{user_id}` | Autenticado | Obtiene el detalle y reputación de un usuario específico (404 si no existe). |
| `POST` | `/usuarios/` | Solo Admin (403) | Creación administrativa directa de usuarios en la plataforma. |
| `PUT` | `/usuarios/{user_id}` | Admin o Propietario | Actualización administrativa de información de un usuario. |
| `DELETE` | `/usuarios/{user_id}` | Solo Admin (403) | Eliminación de un usuario del sistema (código 204 No Content). |
| `POST` | `/admin/users/{id}/promote` | Solo Admin (403) | Promueve a un usuario al rol privilegiado de 'moderador'. |
| `POST` | `/publicaciones/` | Estudiante (Token) | Registra un libro oculto hasta demostrar posesión y recibir aprobación de moderación. |
| `GET` | `/publicaciones/mis-publicaciones` | Estudiante (Token) | Lista los libros activos e inactivos del usuario autenticado. |
| `POST` | `/publicaciones/{id}/verificacion/desafios` | Propietario (Token) | Genera un código temporal para las fotos de portada y página ISBN. |
| `POST` | `/publicaciones/{id}/verificacion/evidencias` | Propietario (Token) | Sube fotos privadas con código visible; límite 8 MB por foto. |
| `GET` | `/publicaciones/verificaciones/pendientes` | Moderación (Token) | Consulta la cola de evidencias por revisar. |
| `POST` | `/publicaciones/verificaciones/{id}/revision` | Moderación (Token) | Aprueba o rechaza la evidencia; solo la aprobación activa el libro. |
| `GET` | `/publicaciones/verificaciones/{id}/evidencia/{tipo}` | Propietario o moderación | Sirve fotos privadas tras comprobar autorización. |
| `POST` | `/trueques/` | Estudiante (Token) | Propone un trueque entre publicaciones activas y propias/de otro usuario. |
| `GET` | `/trueques/mis-trueques` | Estudiante (Token) | Lista trueques y conversaciones asociados al usuario. |
| `GET/POST` | `/trueques/{id}/mensajes` | Participante (Token) | Lee o envía mensajes de la conversación del trueque. |
| `WS` | `/trueques/{id}/ws` | Participante (JWT bearer) | Recibe mensajes en tiempo real de la conversación. |
| `GET` | `/health` | Público | Health check básico del servidor FastAPI. |
| `GET` | `/health/db` | Público | Health check profundo que prueba la conexión activa con PostgreSQL/SQLite. |

---

## 6. Pruebas Automatizadas y Calidad (QA)

La prueba de integración P2P verifica el registro de libros, autorización entre participantes, mensajes en tiempo real y cierre del chat. La ejecución histórica de la suite base aparece debajo.

| Archivo de Prueba | Función de Prueba | Resultado | Aspecto Validado |
|---|---|---|---|
| `test_user_service.py` | `test_create_user` | **PASSED** | Creación de usuario en dominio y hasheo seguro de contraseña. |
| `test_user_service.py` | `test_get_user` | **PASSED** | Búsqueda por ID y validación de campos de entidad. |
| `test_user_service.py` | `test_update_user` | **PASSED** | Actualización de nombre y datos en servicio de dominio. |
| `test_user_service.py` | `test_delete_user` | **PASSED** | Eliminación y captura de ValueError al consultar borrado. |
| `test_user_crud.py` | `test_user_crud_and_promotion` | **PASSED** | Flujo E2E: registro, login, `/me`, update `/me`, listar y ascenso a moderador. |
| `test_p2p_flow.py` | `test_publish_book_and_complete_authenticated_trade_conversation` | **PASSED** | Publicación, trueque asociado a libros, historial P2P, WebSocket autenticado, permisos y cierre. |
| `test_auth_integration.py` | `test_health_and_database_connection` | **PASSED** | Respuesta de `/health` y conexión real a BD en `/health/db`. |
| `test_auth_integration.py` | `test_login_and_refresh` | **PASSED** | Emisión de Access Token, cookie HttpOnly, refresh y logout. |
| `test_auth_integration.py` | `test_google_oauth_flow` | **PASSED** | Intercambio de código OAuth simulado con Respx y emisión de JWT. |

```text
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\Juan Camilo\Downloads\backendEstudiantil
plugins: anyio-4.3.0, asyncio-1.4.0, respx-0.23.1

backend_estudiantil/tests/test_user_crud.py::test_user_crud_and_promotion PASSED [ 12%]
backend_estudiantil/tests/test_user_service.py::test_create_user PASSED  [ 25%]
backend_estudiantil/tests/test_user_service.py::test_get_user PASSED     [ 37%]
backend_estudiantil/tests/test_user_service.py::test_update_user PASSED  [ 50%]
backend_estudiantil/tests/test_user_service.py::test_delete_user PASSED  [ 62%]
tests/test_auth_integration.py::test_health_and_database_connection PASSED [ 75%]
tests/test_auth_integration.py::test_login_and_refresh PASSED            [ 87%]
tests/test_auth_integration.py::test_google_oauth_flow PASSED            [100%]

============================== 8 passed in 3.56s ==============================
```

---

## 7. Flujo de publicación, trueque y conversación P2P

1. El estudiante autenticado registra un libro con `POST /publicaciones/`. La publicación queda inactiva y oculta mientras se verifica.
2. Solicita `POST /publicaciones/{id}/verificacion/desafios` y toma dos fotos recientes mostrando el código temporal en la portada y en la página del ISBN. El desafío vence en 15 minutos.
3. Envía ambas fotos con `POST /publicaciones/{id}/verificacion/evidencias`. Un administrador o moderador abre la cola de revisión del panel, inspecciona las fotos privadas y aprueba o rechaza; sólo una aprobación vuelve activa la publicación.
4. En el catálogo, el estudiante selecciona una publicación propia activa y otra publicación activa, y envía `POST /trueques/` con `publicacion_origen_id` y `publicacion_destino_id`.
5. Los dos participantes consultan el historial paginado y se envían mensajes con `GET/POST /trueques/{id}/mensajes`. Redis distribuye los nuevos eventos mediante `WS /trueques/{id}/ws`, autenticado con el token como subprotocolo `bearer`.
6. El receptor puede confirmar; cualquiera de los participantes puede completar. Rechazar o completar archiva la conversación y bloquea nuevos mensajes.

No se aceptan mensajes ni conexiones WebSocket de usuarios ajenos al trueque. Las fotos de verificación no son públicas, se normalizan para retirar metadatos y la revisión inicial es humana. El código ayuda a evitar fotos recicladas, pero no demuestra por sí solo que un libro sea genuino. No se usa biometría ni se activa un modelo neuronal sin datos etiquetados revisados.

---

## 8. Guía de Puesta en Marcha y Despliegue

```bash
# 1. Instalar dependencias
pip install -r backend_estudiantil/requirements.txt

# 2. Configurar .env
cp backend_estudiantil/.env.example .env

# 3. Ejecutar la API
uvicorn backend_estudiantil.infrastructure.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Explorar Swagger
http://localhost:8000/docs
```
