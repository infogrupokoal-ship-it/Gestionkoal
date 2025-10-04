# Gestión Koal - Aplicación de Gestión de Servicios

## Descripción

Esta es la aplicación de gestión de servicios de Grupo Koal, diseñada para optimizar la administración de trabajos, clientes, materiales, proveedores y más. Incluye funcionalidades como gestión de trabajos, cotizaciones vía WhatsApp, estudio de mercado y autenticación de usuarios.

## Configuración del Entorno de Desarrollo

Sigue estos pasos para configurar y ejecutar el proyecto en tu máquina local.

### 1. Clonar el Repositorio

```bash
git clone https://github.com/infogrupokoal-ship-it/Gestionkoal.git
cd Gestionkoal
```

### 2. Crear y Activar el Entorno Virtual

Es altamente recomendable usar un entorno virtual para gestionar las dependencias del proyecto.

```bash
python -m venv .venv
# En Windows
.venv\Scripts\activate
# En macOS/Linux
source .venv/bin/activate
```

### 3. Instalar Dependencias

Instala todas las librerías necesarias usando `pip`.

```bash
pip install -r requirements.txt
```

### 4. Inicializar la Base de Datos

La aplicación utiliza SQLite. Necesitas inicializar la base de datos y poblarla con datos de ejemplo.

```bash
flask --app app init-db
```

### 5. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables (ejemplo):

```
SECRET_KEY='tu_clave_secreta_aleatoria'
DATABASE_PATH='instance/gestion_avisos.sqlite'
UPLOAD_FOLDER='uploads'
FLASK_APP='app.py'

# Configuración de WhatsApp (Meta Cloud API)
WHATSAPP_ACCESS_TOKEN='tu_token_de_acceso_de_whatsapp'
WHATSAPP_PHONE_NUMBER_ID='tu_id_de_numero_de_telefono_de_whatsapp'
WHATSAPP_APP_ID='tu_id_de_aplicacion_de_whatsapp'
WHATSAPP_APP_SECRET='tu_secreto_de_aplicacion_de_whatsapp'
WHATSAPP_VERIFY_TOKEN='tu_token_de_verificacion_de_webhook'
GEMINI_API_KEY='tu_clave_api_de_gemini'
```

### 6. Ejecutar la Aplicación

#### Modo Desarrollo

```bash
flask --app app run --debug
```

La aplicación estará disponible en `http://127.0.0.1:5000`.

#### Modo Producción (usando Waitress)

```bash
waitress-serve --host=0.0.0.0 --port=5000 --call app:create_app
```

## Características Clave

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
