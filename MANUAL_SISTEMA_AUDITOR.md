# Plataforma de Trueque Estudiantil
## Manual de Administrador y Técnico del Sistema Auditor
### Implementación de la Regla de las 5W y Buenas Prácticas de Seguridad

---

**Documento:** Manual Oficial del Sistema Auditor y Seguridad  
**Versión:** 1.0.0  
**Fecha:** Octubre de 2026  
**Autor:** Equipo de Desarrollo de Plataforma de Trueque Estudiantil  
**Entregable Académico:** Punto 6 — Sistema y Módulo Auditor  

---

## 1. Introducción y Propósito del Sistema Auditor

El **Sistema Auditor** es un componente transversal de ciberseguridad, trazabilidad y control de acceso diseñado para registrar, monitorear y evaluar cada interacción sensible que ocurre dentro de la **Plataforma de Trueque Estudiantil**.

### 1.1. Objetivos Principales
1. **Trazabilidad Forense:** Garantizar la reconstrucción cronológica exacta de cualquier incidente, intento de fraude o acción no autorizada.
2. **Cumplimiento de la Regla de las 5W:** Estructurar cada evento bajo las 5 preguntas fundamentales de la auditoría informática: **Who, What, When, Where, Why**.
3. **Detección Temprana de Amenazas:** Identificar ataques de fuerza bruta, escaneo de endpoints, tokens expirados y accesos denegados mediante códigos de estado HTTP (401, 403, 429).
4. **No Repudio e Integridad:** Los registros de auditoría se almacenan en una tabla inmutable (`auditorias`) de la base de datos relacional, accesible únicamente por administradores autenticados.

---

## 2. Arquitectura de 3 Capas del Sistema Auditor

El sistema sigue estrictamente el patrón arquitectónico de tres capas exigido en los lineamientos técnicos:

```
[ Petición Cliente / Web / Móvil ]
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. CAPA DE CAPTURA (AuditMiddleware / Interceptores)         │
│   - Intercepta Requests y Responses en FastAPI              │
│   - Mide tiempo de respuesta (duracion_ms)                  │
│   - Extrae token JWT (Who) e IP del cliente                 │
│   - Clasifica la acción de negocio y recurso (What, Where)  │
│   - Genera Logs estructurados en consola (Generador logs)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Inserción Asíncrona)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CAPA DE ALMACENAMIENTO (Persistencia Segura en BD)       │
│   - Tabla PostgreSQL/SQLite: 'auditorias'                   │
│   - Modelo ORM: AuditoriaLogORM                             │
│   - Índices optimizados en fecha_hora, usuario_id, accion   │
│   - Persistencia inmutable sin endpoints de borrado/edición │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CAPA DE VISUALIZACIÓN (Consola de Administración)        │
│   - Backend: GET /admin/auditoria, GET /admin/auditoria/stats│
│   - Frontend: Panel interactivo en index.html               │
│   - Métricas KPI (Total, Exitosos, Errores, Bloqueos 401/403)│
│   - Filtros en vivo por acción, errores o búsqueda de texto │
│   - Modal detallado con desglose visual de las 5W           │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Implementación Detallada de la Regla de las 5W

Cada registro generado por el interceptor middleware contiene los siguientes campos normalizados:

| Pregunta 5W | Campo en Base de Datos | Tipo | Descripción | Ejemplo |
|---|---|---|---|---|
| **WHO** *(¿Quién?)* | `usuario_id`<br>`usuario_email`<br>`usuario_rol`<br>`ip_origen`<br>`user_agent` | `Integer`<br>`String`<br>`String`<br>`String`<br>`String` | Identidad digital del actor. Si la petición es pública o previa a autenticación, se registra como `Anónimo`. Extrae IP real considerando headers proxy (`x-forwarded-for`). | `ID: 15`<br>`camilo@universidad.edu.co`<br>`rol: usuario`<br>`IP: 181.129.45.10` |
| **WHAT** *(¿Qué?)* | `accion`<br>`recurso` | `String(100)`<br>`String(100)` | Acción de negocio ejecutada por el actor y agrupación funcional del recurso afectado. | `INICIO_SESION`<br>`PROPONER_TRUEQUE`<br>`MODERACION_LIBRO_IA`<br>`recurso: trueques` |
| **WHEN** *(¿Cuándo?)* | `fecha_hora` | `DateTime(UTC)` | Marca de tiempo precisa sincronizada en UTC con zona horaria ISO-8601. | `2026-10-13T23:20:15.123Z` |
| **WHERE** *(¿Dónde?)* | `metodo_http`<br>`endpoint` | `String(10)`<br>`String(255)` | Ruta de la API y verbo HTTP solicitado. | `POST /trueques/12/confirmar` |
| **WHY** *(¿Por qué?)* | `estado_http`<br>`exito`<br>`detalle`<br>`duracion_ms` | `Integer`<br>`Boolean`<br>`Text`<br>`Float` | Resultado de la operación, estado del generador de respuesta y justificación/motivo en caso de error. | `HTTP 401`<br>`exito: false`<br>`"No autorizado: token inválido"`<br>`duracion: 14.5 ms` |

---

## 4. Manual de Operaciones para el Administrador

### 4.1. Acceso a la Consola de Auditoría
1. Inicie sesión en la plataforma con una cuenta que tenga el rol de **`administrador`** o **`admin`**.
2. Diríjase a la pestaña **Administración y moderación** en la barra de navegación superior.
3. Desplácese hasta la sección **"Bitácora del Sistema Auditor (Regla de las 5W)"**.

### 4.2. Interpretación de los Indicadores (KPIs)
- **Eventos Auditados:** Muestra el volumen total de peticiones procesadas por el backend.
- **Operaciones Exitosas:** Solicitudes que respondieron con código HTTP 2xx o 3xx.
- **Eventos Fallidos:** Solicitudes que arrojaron códigos 4xx o 5xx. Un incremento abrupto indica posibles anomalías o fallos en clientes.
- **Bloqueos (401/403):** Peticiones rechazadas por falta de autenticación o permisos insuficientes. Fundamental para detectar ataques de fuerza bruta o robo de tokens.

### 4.3. Búsqueda y Filtrado Forense
- **Búsqueda rápida:** Escriba cualquier término en el buscador (IP, correo electrónico, parte de una URL o detalle de error) y presione Enter o el botón *"Filtrar"*.
- **Filtro por Acción:** Seleccione una acción específica para aislar eventos como `INICIO_SESION`, `SUBIR_EVIDENCIA_LIBRO` o `MODERACION_LIBRO_IA`.
- **Filtro Solo Errores:** Permite aislar en un clic todos los eventos con `exito = False` para auditorías de seguridad rápidas.
- **Botón "5W":** Al hacer clic sobre el botón de cada fila, se despliega una ventana modal con el desglose estético y forense completo de las 5W.

---

## 5. Manual Técnico para Desarrolladores

### 5.1. Componentes del Código
- **Middleware Interceptor:** [`backend_estudiantil/infrastructure/audit_middleware.py`](file:///c:/Users/Juan%20Camilo/Downloads/backendEstudiantil/backend_estudiantil/infrastructure/audit_middleware.py)  
  Implementa la clase `AuditMiddleware(BaseHTTPMiddleware)`. Se registra en [`main.py`](file:///c:/Users/Juan%20Camilo/Downloads/backendEstudiantil/backend_estudiantil/infrastructure/main.py) mediante `app.add_middleware(AuditMiddleware)`.
- **Modelo de Base de Datos:** [`backend_estudiantil/adapters/db/__init__.py`](file:///c:/Users/Juan%20Camilo/Downloads/backendEstudiantil/backend_estudiantil/adapters/db/__init__.py)  
  Contiene la clase `AuditoriaLogORM` asociada a la tabla `auditorias`.
- **API REST y Control RBAC:** [`backend_estudiantil/infrastructure/api/admin_router.py`](file:///c:/Users/Juan%20Camilo/Downloads/backendEstudiantil/backend_estudiantil/infrastructure/api/admin_router.py)  
  Endpoints protegidos por dependencia `get_current_user` con validación de rol `admin`/`administrador`:
  - `GET /admin/auditoria`: Consulta paginada y filtrada.
  - `GET /admin/auditoria/stats`: KPIs consolidados en tiempo real.
- **Capa Cliente (Frontend):**
  - Consumo en [`frontend/js/api.js`](file:///c:/Users/Juan%20Camilo/Downloads/backendEstudiantil/frontend/js/api.js) (`getAuditLogs`, `getAuditStats`).
  - Renderizado en [`frontend/js/app.js`](file:///c:/Users/Juan%20Camilo/Downloads/backendEstudiantil/frontend/js/app.js) (`loadAuditLogs`, `showAuditDetail`).
  - Interfaz en [`frontend/index.html`](file:///c:/Users/Juan%20Camilo/Downloads/backendEstudiantil/frontend/index.html).

### 5.2. Buenas Prácticas de Seguridad Implementadas
1. **Persistencia No Bloqueante:** El registro en base de datos se ejecuta mediante `asyncio.create_task`, evitando agregar latencia a las peticiones del usuario final.
2. **Tolerancia a Fallos (Failsafe):** Si la base de datos llega a fallar momentáneamente, el interceptor captura la excepción en un bloque `try/except` y emite un log de emergencia sin interrumpir la respuesta al cliente.
3. **Manejo Seguro de Identidad:** La decodificación del JWT se realiza de forma pasiva; tokens manipulados o expirados no generan caídas del servidor, sino que se auditan como accesos fallidos.
4. **Protección contra Inyección y Paginación:** Las consultas de auditoría usan SQLAlchemy 2.0 parametrizado con límites estrictos (`limit <= 200`) para evitar ataques de denegación de servicio (DoS) sobre la base de datos.
5. **Sanitización de Datos Sensibles:** Nunca se almacenan contraseñas en texto plano ni tokens completos en el campo `detalle`.
