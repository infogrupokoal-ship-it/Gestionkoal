# Informe de Descubrimiento del Proyecto

## 1. Configuración de la Aplicación Flask

- **Módulo Flask:** `backend:create_app()` (Patrón App Factory detectado en `backend/__init__.py`).
- **Puerto Local:** No definido explícitamente. Usará el puerto por defecto de Flask (`5000`).
- **Ruta de Health Check:** `/health` (definida en `backend/__init__.py`).

## 2. Endpoints de Webhooks

- **Ruta de Webhook WhatsApp (Meta):** `/webhooks/whatsapp` (definida en `backend/whatsapp_meta.py`). La ruta completa es manejada por el blueprint.
- **Cabeceras de Seguridad:** El código en `whatsapp_meta.py` busca la variable de entorno `WHATSAPP_APP_SECRET` para validar la firma `X-Hub-Signature-256`.

## 3. Scripts Existentes

Se han detectado los siguientes scripts para la automatización de tareas:

- `00_setup_venv.bat`: Probablemente para configurar el entorno virtual.
- `02_run_dev.bat`: Para ejecutar el servidor de desarrollo.
- `03_run_prod_waitress.bat`: Para ejecutar el servidor en modo producción con Waitress.
- `04_init_db.bat`: Para inicializar la base de datos.
- `iniciokoal.bat`, `koal.bat`: Scripts de propósito general o de arranque.
- `logtail.ps1`, `scripts/run_local.ps1`: Scripts de PowerShell para visualización de logs y ejecución local.

## 4. Base de Datos (ORM)

- **Tipo de BD:** SQLite (configurado en `backend/__init__.py`).
- **ORM:** Flask-SQLAlchemy y Flask-Migrate están en uso.
- **Directorio de Migraciones:** `migrations/` existe en la raíz del proyecto.
- **Comando de Migración:** `flask db <comando>`.

## 5. Integración IA (Gemini)

- **Módulo Principal:** `backend/ia_command.py` (singular).
- **Invocación:** A través de un endpoint que llama a la lógica en `_handle_ia_command_logic`.
- **Variables Requeridas:** `GEMINI_API_KEY` o `GOOGLE_API_KEY` (detectado en `backend/ai_chat.py`).
