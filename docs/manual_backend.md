# Manual Técnico del Backend - Gestión Koal

Este documento detalla la arquitectura, configuración y buenas prácticas para el desarrollo y mantenimiento del backend de la aplicación Gestión Koal.

## 1. Cómo Lanzar el Proyecto Localmente

Para poner en marcha el backend de Gestión Koal en tu entorno local, sigue estos pasos:

1.  **Clonar el Repositorio:**
    ```bash
    git clone https://github.com/infogrupokoal-ship-it/Gestionkoal.git
    cd Gestionkoal
    ```

2.  **Crear y Activar el Entorno Virtual:**
    ```bash
    python -m venv .venv
    # En Windows
    .venv\Scripts\activate
    # En macOS/Linux
    source .venv/bin/activate
    ```

3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar Variables de Entorno:**
    Crea un archivo `.env` en la raíz del proyecto con las siguientes variables (puedes usar `.env.example` como plantilla):
    ```
    SECRET_KEY='tu_clave_secreta_aqui'
    DATABASE_PATH='instance/gestion_avisos.sqlite'
    UPLOAD_FOLDER='uploads'
    FLASK_APP=backend
    FLASK_ENV=development
    # Otras variables como API keys de Gemini, WhatsApp, etc.
    GEMINI_API_KEY='tu_gemini_api_key'
    WAHA_URL='http://localhost:3000'
    WAHA_WEBHOOK_URL='http://tu_ngrok_url/api/whatsapp/webhook'
    ```

5.  **Inicializar la Base de Datos:**
    ```bash
    flask init-db
    ```

6.  **Sembrar la Base de Datos (Opcional):**
    ```bash
    flask seed
    ```

7.  **Ejecutar la Aplicación:**
    ```bash
    flask run
    ```
    La aplicación estará disponible en `http://127.0.0.1:5000`.

## 2. Cómo Cargar Datos con Gemini

Gemini puede interactuar con la aplicación para cargar datos de prueba o realizar operaciones. Utiliza los scripts de automatización o las herramientas CLI proporcionadas para facilitar esta interacción.

## 3. Cómo Hacer Backup/Import de Datos

### Backup
La base de datos principal es `instance/gestion_avisos.sqlite`. Para hacer un backup, simplemente copia este archivo a una ubicación segura.

### Import
Para importar una base de datos, reemplaza el archivo `instance/gestion_avisos.sqlite` existente con tu archivo de backup. Asegúrate de detener la aplicación Flask antes de realizar esta operación.

## 4. Estructura de la Base de Datos

La base de datos se define en `schema.sql` y se gestiona con Flask-Migrate. Las tablas clave incluyen:

*   `users`: Gestión de usuarios y roles.
*   `roles`: Definición de roles y permisos.
*   `clients`: Información de clientes.
*   `providers`: Información de proveedores.
*   `materiales`: Inventario de materiales.
*   `servicios`: Catálogo de servicios.
*   `tickets`: Trabajos o tareas.
*   `job_materials`: Materiales asociados a un trabajo.
*   `job_services`: Servicios asociados a un trabajo.
*   `activity_log`: Registro de actividades.
*   `quotes`: Cotizaciones.
*   `market_research`: Datos de estudio de mercado.
*   `provider_quotes`: Cotizaciones de proveedores.
*   `quick_tasks`: Tareas rápidas.
*   `notifications`: Notificaciones de usuario.
*   `gastos`: Registro de gastos.

## 5. Cómo Extender Funcionalidades

### Añadir Nuevos Roles y Permisos
1.  Define el nuevo rol en la tabla `roles` de `schema.sql` o mediante una migración.
2.  Asigna los permisos necesarios al nuevo rol en la tabla `role_permissions`.
3.  Utiliza el decorador `@permission_required('nombre_del_permiso')` en las rutas de Flask para proteger las funcionalidades.

### Añadir Nuevos Blueprints
1.  Crea un nuevo archivo Python en la carpeta `backend/` (ej. `backend/new_feature.py`).
2.  Define un `Blueprint` en este archivo.
3.  Implementa las rutas y la lógica de negocio.
4.  Registra el nuevo blueprint en `backend/__init__.py`.

## 6. Organización de Blueprints y Rutas

El backend está organizado en blueprints, cada uno encapsulando funcionalidades relacionadas. Los blueprints se registran en `backend/__init__.py`.

*   `auth`: Autenticación de usuarios (login, registro, logout).
*   `clients`: Gestión de clientes.
*   `providers`: Gestión de proveedores.
*   `materials`: Gestión de materiales.
*   `jobs`: Gestión de trabajos/tareas.
*   `services`: Gestión de servicios.
*   `admin`: Funcionalidades de administración (gestión de usuarios, analíticas).
*   `profile`: Perfil de usuario.
*   `feedback`: Envío de feedback.
*   `quick_task`: Tareas rápidas.
*   `analytics`: Endpoints para datos de gráficos del dashboard.
*   `search`: Funcionalidad de búsqueda global.
*   `reorder`: Gestión de puntos de reorden.
*   `whatsapp_meta`: Integración con la API de WhatsApp Business.
*   `ia_commands`: Comandos de IA.

## 7. Estructura de Carpetas y Archivos Clave

*   `backend/`: Contiene toda la lógica del servidor Flask.
    *   `__init__.py`: Inicialización de la aplicación y registro de blueprints.
    *   `models.py`: Definición de modelos de base de datos (SQLAlchemy).
    *   `schema.sql`: Esquema inicial de la base de datos.
    *   `forms.py`: Definición de formularios (Flask-WTF).
    *   `cli.py`: Comandos de línea de comandos personalizados.
    *   `extensions.py`: Extensiones de Flask (SQLAlchemy, Flask-Login, etc.).
    *   `auth.py`: Lógica de autenticación y autorización.
    *   `db_utils.py`: Utilidades para la base de datos.
    *   `data_quality.py`: Funciones para el control de calidad de datos.
    *   `analytics.py`: Endpoints para datos analíticos.
    *   `blueprints/`: (Opcional, para proyectos más grandes) Subcarpetas para organizar blueprints.
*   `templates/`: Archivos HTML Jinja2 para la interfaz de usuario.
    *   `base.html`: Plantilla base.
    *   `dashboard.html`: Panel de control principal.
    *   `auth/`, `clients/`, `materials/`, etc.: Subcarpetas para plantillas específicas de cada blueprint.
*   `static/`: Archivos estáticos (CSS, JavaScript, imágenes).
    *   `style.css`: Estilos CSS principales.
    *   `img/`: Imágenes.
*   `instance/`: Contiene la base de datos SQLite (`gestion_avisos.sqlite`) y otros archivos de instancia.
*   `migrations/`: Archivos de migración de la base de datos (Flask-Migrate).
*   `docs/`: Documentación del proyecto.

## 8. Buenas Prácticas y Estilo de Código

*   **PEP 8:** Seguir las guías de estilo de Python (PEP 8).
*   **Comentarios:** Comentar el código cuando sea necesario para explicar lógica compleja o decisiones de diseño.
*   **Docstrings:** Utilizar docstrings para funciones, clases y módulos.
*   **Nomenclatura:** Usar nombres descriptivos para variables, funciones y clases.
*   **Modularidad:** Mantener los blueprints y funciones con un único propósito.
*   **Seguridad:** Validar siempre la entrada del usuario y utilizar parámetros en las consultas SQL para prevenir inyecciones.
*   **Manejo de Errores:** Implementar un manejo de errores robusto y registrar los errores.
*   **Consistencia:** Mantener la consistencia en el estilo de código y la estructura del proyecto.

---

**Próximos pasos para la documentación:**

*   Detallar la estructura de la base de datos con un diagrama o listado de tablas y sus relaciones.
*   Añadir ejemplos de uso de Gemini para tareas específicas.
*   Documentar el frontend (si se requiere).
*   Crear un manual para usuarios funcionales.
