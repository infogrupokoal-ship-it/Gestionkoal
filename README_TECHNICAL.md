# README Técnico: Gestionkoal

## 1. Resumen del Proyecto

**Gestionkoal** es una aplicación web Flask diseñada para la gestión integral de servicios, clientes, trabajos y métricas de negocio. El sistema está construido con una arquitectura modular basada en Blueprints de Flask, lo que permite una separación clara de las responsabilidades y facilita la escalabilidad.

Este documento describe la arquitectura técnica, la configuración del entorno, el proceso de despliegue y las convenciones de código del proyecto.

## 2. Arquitectura del Software

El proyecto sigue una estructura organizada para separar la lógica de negocio, la presentación y los datos.

-   `backend/`: Contiene la lógica principal de la aplicación, organizada en **Blueprints** de Flask.
    -   `__init__.py`: Fábrica de la aplicación (`create_app`), donde se inicializan las extensiones y se registran los blueprints.
    -   `auth.py`: Gestión de autenticación, registro y sesiones de usuario.
    -   `clients.py`: Lógica de negocio para la gestión de clientes.
    -   `jobs.py`: Lógica de negocio para la gestión de trabajos/tareas.
    -   `metrics.py`: Endpoints y funciones para calcular y exponer KPIs del negocio.
    -   `db.py`: Módulo de inicialización de la base de datos y comandos `flask init-db`.
    -   `models.py`: (Futuro) Definiciones de modelos de SQLAlchemy ORM.
-   `templates/`: Contiene las plantillas HTML (Jinja2) que renderizan las vistas de la aplicación. La estructura de carpetas dentro de `templates/` refleja los blueprints.
-   `static/`: Almacena los archivos estáticos como hojas de estilo CSS, JavaScript del lado del cliente e imágenes.
-   `tests/`: Directorio con todas las pruebas automatizadas.
    -   `test_api.py`: Pruebas de integración para los endpoints de la API (ej. `/api/metrics`).
    -   `test_views.py`: Pruebas de integración para las vistas de Flask (ej. `/dashboard`).
    -   `conftest.py`: Fixtures de Pytest para configurar el entorno de pruebas (ej. cliente de prueba, inicialización de BD de prueba).
-   `instance/`: Directorio (ignorado por Git) donde se almacena la base de datos SQLite (`gestion_avisos.sqlite`) y otros archivos de instancia.
-   `migrations/`: (Futuro) Directorio para las migraciones de la base de datos generadas por Flask-Migrate.

## 3. Configuración del Entorno de Desarrollo

Sigue estos pasos para configurar un entorno de desarrollo local.

**Requisitos:**
-   Python 3.10+
-   Git

**Pasos:**

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/infogrupokoal-ship-it/Gestionkoal.git
    cd Gestionkoal
    ```

2.  **Crear y activar un entorno virtual:**
    ```bash
    # En Windows
    python -m venv .venv
    .venv\Scripts\activate

    # En macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar variables de entorno:**
    Crea un archivo `.flaskenv` en la raíz del proyecto con el siguiente contenido:
    ```
    FLASK_APP=backend:create_app
    FLASK_DEBUG=1
    ```

5.  **Inicializar la base de datos:**
    Este comando creará el archivo `instance/gestion_avisos.sqlite` y ejecutará el schema.
    ```bash
    flask init-db
    ```
    Si la base de datos ya existe, este comando la reiniciará.

## 4. Ejecución de la Aplicación

Con el entorno configurado, puedes iniciar el servidor de desarrollo:

```bash
flask run
```

La aplicación estará disponible en `http://127.0.0.1:5000`.

## 5. Ejecución de Pruebas

El proyecto utiliza `pytest` para las pruebas automatizadas. Las pruebas se ejecutan en una base de datos SQLite en memoria para garantizar el aislamiento y la velocidad.

Para ejecutar todas las pruebas, simplemente corre:

```bash
pytest
```

El resultado mostrará el estado de cada prueba (pasada, fallida, etc.) y un resumen final.

## 6. Gestión de la Base de Datos

-   **Tecnología:** SQLAlchemy Core para la ejecución de consultas SQL crudas y `sqlite3` como motor de base de datos en desarrollo y pruebas.
-   **Schema:** La estructura inicial de la base de datos se define en `backend/schema.sql`.
-   **Inicialización:** El comando `flask init-db` (definido en `backend/db.py`) se encarga de crear o recrear la base de datos a partir del schema.
-   **Migraciones:** Para futuras actualizaciones del esquema en producción, se integrará `Flask-Migrate`.

## 7. Plan de Despliegue (Render)

Esta sección describe el plan para desplegar la aplicación en la plataforma Render.

**Estrategia:**
Se utilizará un servicio "Web Service" en Render configurado para ejecutar una aplicación Python. El despliegue será automático a partir de los commits a la rama `main` del repositorio de GitHub.

**Artefactos necesarios:**

1.  **`render.yaml`:** Un archivo de "Infraestructura como Código" que define todos los servicios y configuraciones.
    -   **Servicio:** `web`
    -   **Entorno:** `python`
    -   **Comando de Build:** `pip install -r requirements.txt`
    -   **Comando de Inicio:** `gunicorn "backend:create_app()"` (o `waitress-serve`)
    -   **Disco Persistente:** Se montará un disco en `/instance` para que la base de datos SQLite sea persistente entre despliegues.

2.  **`Dockerfile` (Alternativa):** Como alternativa a los buildpacks de Render, se puede usar un `Dockerfile` para tener un control total sobre el entorno de ejecución.

**Pasos de implementación:**

1.  **Crear `render.yaml`:** Definir el servicio web, el build, el comando de inicio y el disco persistente.
2.  **Ajustar el comando de inicio:** Usar un servidor WSGI de producción como Gunicorn o Waitress.
    -   Ejemplo con Waitress: `waitress-serve --host=0.0.0.0 --port=$PORT "backend:create_app()"`
3.  **Añadir Health Check:** Implementar un endpoint simple como `/healthz` que devuelva un `200 OK` para que Render pueda verificar el estado de la aplicación.
4.  **Configurar variables de entorno en Render:**
    -   `FLASK_APP`: `backend:create_app`
    -   `SECRET_KEY`: Un valor secreto y único.
    -   `DATABASE_URL`: La ruta al archivo de la base de datos en el disco persistente (ej. `/instance/gestion_avisos.sqlite`).