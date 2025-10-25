# Checkpoint del Proyecto Gestionkoal

**Fecha:** 21 de octubre de 2025

## 1. Resumen del Proyecto
El proyecto "Gestionkoal" es una aplicación web basada en Flask para la gestión de servicios, clientes, trabajos, materiales, inventario y autenticación de usuarios. Incluye un dashboard con calendario y una lista de trabajos próximos. Se están implementando funcionalidades avanzadas como un asistente de IA, integración con WhatsApp, y mejoras en el estudio de mercado.

## 2. Estado Actual del Proyecto
Hemos estado trabajando en la configuración de las pruebas unitarias con `pytest` y resolviendo problemas relacionados con la reflexión de tablas de SQLAlchemy en un entorno de prueba con SQLite en memoria.

### 2.1. Archivos Clave y su Estado Actual

#### `backend/db.py`
-   **Modificación:** La función `_execute_sql` fue modificada para manejar múltiples sentencias SQL, dividiendo el string SQL por punto y coma y ejecutando cada una individualmente.
-   **Estado:** Estable.

#### `backend/models.py`
-   **Modificaciones:**
    -   Las definiciones de las clases `User`, `Role`, y `UserRole` (modelos DeclarativeBase) se movieron al inicio del archivo, justo después de `DeclarativeBase = declarative_base()`.
    -   La importación de `current_app` se movió a la parte superior del archivo, eliminando el bloque `try...except` alrededor de ella.
    -   La función `_prepare_mappings()` fue modificada para:
        -   Declarar `Base` como global.
        -   Inicializar `Base` con `metadata=flask_sqlalchemy_db.metadata` dentro del bloque `if current_app...`.
        -   Luego procede con `Base.metadata.clear()`, `flask_sqlalchemy_db.metadata.reflect(bind=engine)` y `Base.prepare(engine)`.
-   **Estado:** En proceso de depuración. La última modificación busca resolver el problema de reflexión de tablas.

#### `tests/conftest.py`
-   **Modificaciones:**
    -   Se eliminó la doble llamada a `db.init_app(app)`.
    -   Se importó `_execute_sql` desde `backend.db`.
    -   Se corrigió la indentación de varias líneas.
    -   Se movió la llamada a `_prepare_mappings()` a la posición correcta dentro del fixture `app()`.
    -   Se añadió un `print` de depuración para listar las tablas en la base de datos antes de `_prepare_mappings()`.
    -   Se eliminó `Base` de la lista de importación.
    -   Se añadió `_prepare_mappings` de nuevo a la lista de importación.
-   **Estado:** En proceso de depuración.

## 3. Problemas Encontrados y Soluciones Aplicadas

### Problema 1: `pytest` no reconocido
-   **Error:** `"pytest" no se reconoce como un comando interno o externo...`
-   **Solución:** Ejecutar `pytest` usando el intérprete de Python del entorno virtual: `.venv\Scripts\python.exe -m pytest`.

### Problema 2: `NameError: name '_execute_sql' is not defined`
-   **Error:** `NameError: name '_execute_sql' is not defined` en `tests/conftest.py`.
-   **Solución:** Importar `_execute_sql` desde `backend.db` en `tests/conftest.py`.

### Problema 3: `sqlite3.ProgrammingError: You can only execute one statement at a time.`
-   **Error:** `sqlite3.ProgrammingError: You can only execute one statement at a time.` al ejecutar `schema.sql`.
-   **Solución:** Modificar `_execute_sql` en `backend/db.py` para dividir el string SQL en sentencias individuales y ejecutarlas una por una.

### Problema 4: `RuntimeError: The current Flask app is not registered with this 'SQLAlchemy' instance.`
-   **Error:** `RuntimeError: The current Flask app is not registered with this 'SQLAlchemy' instance.` al llamar `DeclarativeBase.metadata.create_all(db.engine)`.
-   **Solución:** Re-añadir `db.init_app(app)` dentro del `app_context` en `tests/conftest.py` para inicializar correctamente SQLAlchemy para las pruebas.

### Problema 5: `LookupError: Tabla no encontrada en metadata reflejada: clientes` y `DEBUG: Automap reflected tables: []`
-   **Error:** La tabla `clientes` no se refleja, a pesar de existir en la base de datos en memoria. `DEBUG: Automap reflected tables: []` está vacío.
-   **Soluciones Intentadas:**
    -   Reordenar la ejecución de `_execute_sql` y `DeclarativeBase.metadata.create_all`.
    -   Añadir `Base.metadata.clear()` antes de `Base.metadata.reflect()`.
    -   Usar `Base.metadata.reflect(bind=engine)` en lugar de `Base.prepare(autoload_with=engine)`.
    -   Intentar vincular `Base.metadata` a `db.metadata` (causó `NameError`).
    -   Mover las definiciones de `User`, `Role`, `UserRole` al inicio de `backend/models.py`.
    -   Mover la importación de `current_app` al inicio de `backend/models.py`.
    -   Modificar `_prepare_mappings` para inicializar `Base` con `metadata=flask_sqlalchemy_db.metadata` dentro de la función.
-   **Estado Actual:** El problema persiste. La última solución intentada fue modificar `_prepare_mappings` para inicializar `Base` con `metadata=flask_sqlalchemy_db.metadata` dentro de la función, asegurando que la `Base` global se actualice.

### Problema 6: `IndentationError: unexpected indent`
-   **Error:** Errores de indentación en `tests/conftest.py` debido a operaciones de `replace`.
-   **Solución:** Corrección manual de la indentación en `tests/conftest.py`.

### Problema 7: `NameError: name 'db' is not defined`
-   **Error:** `NameError: name 'db' is not defined` en `backend/models.py` al intentar acceder a `db.metadata`.
-   **Solución:** Revertir el cambio que intentaba asignar `Base.metadata = db.metadata` y reevaluar la estrategia de vinculación de metadatos.

### Problema 8: `NameError: name 'current_app' is not defined`
-   **Error:** `NameError: name 'current_app' is not defined` dentro de `_ensure_engine()` en `backend/models.py`.
-   **Solución:** Mover la importación de `current_app` a la parte superior de `backend/models.py` y eliminar el bloque `try...except` alrededor de ella.

## 4. Tareas Pendientes
-   Resolver el `LookupError: Tabla no encontrada en metadata reflejada: clientes` y asegurar que `Base.prepare()` refleje correctamente todas las tablas en el entorno de prueba.
-   Una vez que las pruebas pasen, eliminar los `print` de depuración.
-   Continuar con la implementación de las fases del roadmap.

## 5. Roadmap del Proyecto (Recordatorio)

### Fase 0 (1–2 sprints) – Saneamiento UX/Navegación
*   Auditoría de menús/submenús + estados vacíos + breadcrumbs.
*   Botón WhatsApp genérico + autocompletado transversal.
*   Panel “Tarea rápida”.

### Fase 1 – Comercial y operación
*   Cotización → aceptación → trabajo (PDF + envío simple).
*   Bitácora/timeline + adjuntos.
*   Agenda/dispatch liviano con confirmación de campo.

### Fase 2 – Inventario y proveedores
*   Movimientos básicos + reorden.
*   Solicitudes de precio documentadas.

### Fase 3 – Finanzas y KPIs
*   Facturación básica + partes de horas.
*   Liquidaciones simples a autónomos.
*   KPIs esenciales + panel por rol.

### Fase 4 – IA contextual
*   Sugerencias de próximos pasos.
*   Resúmenes y búsqueda semántica interna.

### Fase 5 – Integraciones y despliegue
*   WhatsApp “plantillas”.
*   Correo y documentos.
*   Render estable.

## 6. Información Adicional
-   **Repo GitHub:** https://github.com/infogrupokoal-ship-it/Gestionkoal.git
-   **Variables locales:** `DB_PATH=database.db`, `UPLOAD_FOLDER=uploads`, `FLASK_APP=app.py`
-   **Render New Web Service Configuration:** (Detalles proporcionados anteriormente en la memoria)
-   **Gemini API Key (Test):** `AIzaSyDZuzsA2qEde_oZ-9D_ag06cDyHwu8XGz8` (expira en 1 año).
-   **WAHA (WhatsApp API) Setup:** Para iniciar los servicios de IA de WhatsApp, el usuario debe ejecutar `agent_scripts/start_whatsapp_services.bat`.
-   **Datos de facturación de la empresa:** Climatizacion Vertical s.l.u, CIF B40642555, Avenida Malvarrosa 112 bajo, Valencia 46011.
-   **Preferencias del usuario:**
    -   Prefiere que yo ejecute el servidor de desarrollo localmente para depurar errores.
    -   Prefiere que yo trabaje de forma más autónoma y agrupe cambios relacionados.
    -   Prefiere que le informe sobre la duración de las tareas.
    -   Prefiere que le comunique los errores antes de desplegar en Render.
    -   Prefiere comandos PowerShell en lugar de `cmd.exe`.

## 7. Últimos Outputs de Depuración Relevantes

```
DEBUG: Tables in DB before _prepare_mappings: ['roles', 'sqlite_sequence', 'users', 'user_roles', 'clientes', 'direcciones', 'equipos', 'tickets', 'ticket_mensajes', 'eventos', 'checklists', 'checklist_items', 'evento_checklist_valores', 'services', 'materiales', 'stock_movs', 'proveedores', 'freelancers', 'mantenimientos_programados', 'herramientas', 'prestamos_herramienta', 'presupuestos', 'presupuesto_items', 'facturas', 'garantias', 'ficheros', 'consentimientos', 'auditoria', 'error_log', 'notifications', 'material_precios_externos', 'estudio_mercado', 'gastos_compartidos', 'whatsapp_message_logs', 'ticket_tareas']
DEBUG: Automap reflected tables: []
```

Este output confirma que las tablas existen en la base de datos, pero `automap_base` no las está reflejando correctamente. La última solución intentada busca resolver este problema vinculando correctamente el objeto `Base` con los metadatos de Flask-SQLAlchemy.
