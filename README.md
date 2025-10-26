# Gestión Koal - Aplicación de Gestión de Servicios

## Descripción

Esta es la aplicación de gestión de servicios de Grupo Koal, diseñada para optimizar la administración de trabajos, clientes, materiales, proveedores y más. Incluye funcionalidades como gestión de trabajos, cotizaciones vía WhatsApp, estudio de mercado y autenticación de usuarios.

## Configuración del Entorno de Desarrollo

Sigue estos pasos para configurar y ejecutar el proyecto en tu máquina local.

### Método Rápido (Recomendado)

Hemos creado scripts para automatizar todo el proceso de configuración y arranque. Simplemente ejecuta el script correspondiente a tu sistema operativo desde la raíz del proyecto.

**En Windows (PowerShell):**

```powershell
.\scripts\run_local.ps1
```

**En macOS/Linux (Bash):**

```bash
chmod +x ./scripts/run_local.sh
./scripts/run_local.sh
```

Estos scripts se encargarán de:
1. Crear un entorno virtual (`.venv`).
2. Instalar todas las dependencias de `requirements.txt`.
3. Aplicar las migraciones de la base de datos (`flask db upgrade`).
4. Sembrar la base de datos con datos iniciales (`flask seed`).
5. Iniciar el servidor de desarrollo en `http://127.0.0.1:5000`.

### Método Manual

Si prefieres configurar el entorno paso a paso:

1.  **Clonar el Repositorio**

    ```bash
    git clone https://github.com/infogrupokoal-ship-it/Gestionkoal.git
    cd Gestionkoal
    ```

2.  **Crear y Activar el Entorno Virtual**

    ```bash
    python -m venv .venv
    # En Windows
    .venv\Scripts\activate
    # En macOS/Linux
    source .venv/bin/activate
    ```

3.  **Instalar Dependencias**

    ```bash
    pip install -U pip wheel
    pip install -r requirements.txt
    ```

4.  **Configurar Variables de Entorno**

    Crea un archivo `.env.local` en la raíz del proyecto copiando el ejemplo `.env.example`. Rellena las claves de API que necesites.

    ```bash
    # En Windows (cmd)
    copy .env.example .env.local
    # En macOS/Linux
    cp .env.example .env.local
    ```

5.  **Crear y Sembrar la Base de Datos**

    Aplica las migraciones y luego siembra los datos iniciales.

    ```bash
    # Establece la app de Flask (si no usas .env)
    # export FLASK_APP=backend
    
    flask db upgrade
    flask seed
    ```

6.  **Ejecutar la Aplicación**

    ```bash
    flask run --host=127.0.0.1 --port=5000
    ```

La aplicación estará disponible en `http://127.0.0.1:5000` y el endpoint de salud en `http://127.0.0.1:5000/health`.


## WhatsApp + IA

- Webhook con firma HMAC (X-Hub-Signature-256 + WHATSAPP_APP_SECRET).
- Idempotencia (whatsapp_message_id) y logs inbound/outbound (/whatsapp/logs).
- DRY_RUN en desarrollo (WHATSAPP_DRY_RUN=1).
- Plantillas de respuesta por prioridad y triage IA (modo mock si no hay GEMINI_API_KEY).

## Seguridad

- Rate limiting en /auth/login y webhook.
- CSRF simple en login/registro (token en sesi�n).

## Variables de Entorno Clave

- WhatsApp: WHATSAPP_PROVIDER, WHATSAPP_DRY_RUN, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET.
- IA: GEMINI_API_KEY (o demo).## Características Clave

*   **Gestión de Trabajos:** Creación, edición y seguimiento de trabajos/tickets, incluyendo métodos y estados de pago, provisiones de fondos y fechas de transferencia.
*   **Gestión de Clientes y Proveedores:** Base de datos de contactos con información de WhatsApp y opciones de opt-in.
*   **Gestión de Materiales y Servicios:** Catálogo, control de stock y seguimiento de movimientos.
*   **Cotizaciones por WhatsApp:** Envío de solicitudes de cotización a proveedores y procesamiento automático de sus respuestas para actualizar presupuestos.
*   **Estudio de Mercado:** Análisis de precios, dificultad de trabajos y simulación de búsqueda web para materiales.
*   **Autenticación y Roles de Usuario:** Control de acceso basado en roles con permisos detallados, página de perfil y selección de rol durante el registro.
*   **Asistente de IA (Chat):** Integración de un asistente de IA para soporte y funcionalidades avanzadas.
*   **Gestión de Activos:** Control de herramientas y equipos, incluyendo préstamos y mantenimientos programados.
*   **Notificaciones:** Sistema de notificaciones para eventos importantes y recordatorios vía WhatsApp.
*   **Registro de Errores y Auditoría:** Monitoreo de errores y registro de actividades del usuario.

## Contacto

Para soporte o más información, contacta a [info@grupokoal.com](mailto:info@grupokoal.com).



## Auditor�a

- Vista unificada en /audit/logs con eventos de error_log, whatsapp_logs, i_logs y 
otifications (si existen).
- Filtros simples por ahora v�a navegador; ideal para inspecci�n r�pida en soportes.

## Gu�a R�pida (Windows / PowerShell)

- Crear entorno y dependencias:
  - py -m venv .venv
  - .\.venv\Scripts\Activate.ps1
  - pip install -r requirements.txt
- Variables locales (opcional .env.local):
  - FLASK_APP=backend:create_app
  - WHATSAPP_DRY_RUN=1 (dev)
- Inicializar y ejecutar:
  - python -m flask run (por defecto en 5000)

## Despliegue en Render (resumen)

- Conectar repo, montar Disk (1GB+), variables:
  - DB_PATH=/var/data/database.db, UPLOAD_FOLDER=/var/data/uploads
  - WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET
  - GEMINI_API_KEY (o demo para modo mock)
- Build: pip install -r requirements.txt
- Start: python run_waitress.py o gunicorn "backend:create_app()"

## Variables Clave

- WhatsApp: WHATSAPP_PROVIDER (meta|twilio), WHATSAPP_DRY_RUN, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET
- IA: GEMINI_API_KEY, GEMINI_MODEL
- Seguridad: SECRET_KEY, SESSION_COOKIE_SECURE=1 (prod)

## Auditor�a y Logs

- Vista unificada en /audit/logs (error_log, whatsapp_logs, ai_logs, notifications).
- Logs WhatsApp con filtros en /whatsapp/logs.
