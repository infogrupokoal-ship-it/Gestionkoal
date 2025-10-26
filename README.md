# Gesti贸n Koal - Aplicaci贸n de Gesti贸n de Servicios

## Descripci贸n

Esta es la aplicaci贸n de gesti贸n de servicios de Grupo Koal, dise帽ada para optimizar la administraci贸n de trabajos, clientes, materiales, proveedores y m谩s. Incluye funcionalidades como gesti贸n de trabajos, cotizaciones v铆a WhatsApp, estudio de mercado y autenticaci贸n de usuarios.

## Configuraci贸n del Entorno de Desarrollo

Sigue estos pasos para configurar y ejecutar el proyecto en tu m谩quina local.

### M茅todo R谩pido (Recomendado)

Hemos creado scripts para automatizar todo el proceso de configuraci贸n y arranque. Simplemente ejecuta el script correspondiente a tu sistema operativo desde la ra铆z del proyecto.

**En Windows (PowerShell):**

```powershell
.\scripts\run_local.ps1
```

**En macOS/Linux (Bash):**

```bash
chmod +x ./scripts/run_local.sh
./scripts/run_local.sh
```

Estos scripts se encargar谩n de:
1. Crear un entorno virtual (`.venv`).
2. Instalar todas las dependencias de `requirements.txt`.
3. Aplicar las migraciones de la base de datos (`flask db upgrade`).
4. Sembrar la base de datos con datos iniciales (`flask seed`).
5. Iniciar el servidor de desarrollo en `http://127.0.0.1:5000`.

### M茅todo Manual

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

    Crea un archivo `.env.local` en la ra铆z del proyecto copiando el ejemplo `.env.example`. Rellena las claves de API que necesites.

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

6.  **Ejecutar la Aplicaci贸n**

    ```bash
    flask run --host=127.0.0.1 --port=5000
    ```

La aplicaci贸n estar谩 disponible en `http://127.0.0.1:5000` y el endpoint de salud en `http://127.0.0.1:5000/health`.


## WhatsApp + IA

- Webhook con firma HMAC (X-Hub-Signature-256 + WHATSAPP_APP_SECRET).
- Idempotencia (whatsapp_message_id) y logs inbound/outbound (/whatsapp/logs).
- DRY_RUN en desarrollo (WHATSAPP_DRY_RUN=1).
- Plantillas de respuesta por prioridad y triage IA (modo mock si no hay GEMINI_API_KEY).

## Seguridad

- Rate limiting en /auth/login y webhook.
- CSRF simple en login/registro (token en sesi髇).

## Variables de Entorno Clave

- WhatsApp: WHATSAPP_PROVIDER, WHATSAPP_DRY_RUN, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET.
- IA: GEMINI_API_KEY (o demo).## Caracter铆sticas Clave

*   **Gesti贸n de Trabajos:** Creaci贸n, edici贸n y seguimiento de trabajos/tickets, incluyendo m茅todos y estados de pago, provisiones de fondos y fechas de transferencia.
*   **Gesti贸n de Clientes y Proveedores:** Base de datos de contactos con informaci贸n de WhatsApp y opciones de opt-in.
*   **Gesti贸n de Materiales y Servicios:** Cat谩logo, control de stock y seguimiento de movimientos.
*   **Cotizaciones por WhatsApp:** Env铆o de solicitudes de cotizaci贸n a proveedores y procesamiento autom谩tico de sus respuestas para actualizar presupuestos.
*   **Estudio de Mercado:** An谩lisis de precios, dificultad de trabajos y simulaci贸n de b煤squeda web para materiales.
*   **Autenticaci贸n y Roles de Usuario:** Control de acceso basado en roles con permisos detallados, p谩gina de perfil y selecci贸n de rol durante el registro.
*   **Asistente de IA (Chat):** Integraci贸n de un asistente de IA para soporte y funcionalidades avanzadas.
*   **Gesti贸n de Activos:** Control de herramientas y equipos, incluyendo pr茅stamos y mantenimientos programados.
*   **Notificaciones:** Sistema de notificaciones para eventos importantes y recordatorios v铆a WhatsApp.
*   **Registro de Errores y Auditor铆a:** Monitoreo de errores y registro de actividades del usuario.

## Contacto

Para soporte o m谩s informaci贸n, contacta a [info@grupokoal.com](mailto:info@grupokoal.com).



## Auditor韆

- Vista unificada en /audit/logs con eventos de error_log, whatsapp_logs, i_logs y 
otifications (si existen).
- Filtros simples por ahora v韆 navegador; ideal para inspecci髇 r醦ida en soportes.
