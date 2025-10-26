# README: Arquitectura de Orquestación con IA

Este documento describe la arquitectura y el flujo de trabajo del sistema de orquestación de avisos (tickets) impulsado por IA (Gemini) en la aplicación Gestionkoal.

## 1. Visión General

El objetivo de este sistema es automatizar el ciclo de vida de un aviso, desde su recepción hasta su resolución. La IA actúa como un coordinador inteligente que se encarga de:

1.  **Ingesta Omnicanal**: Recibir avisos desde WhatsApp, formularios web, etc.
2.  **Triage y Enriquecimiento**: Entender el aviso, clasificarlo, asignarle una prioridad y extraer datos del cliente.
3.  **Deduplicación**: Evitar la creación de tickets duplicados para un mismo problema.
4.  **Asignación Inteligente**: Sugerir o asignar automáticamente el técnico más adecuado.
5.  **Comunicación con el Cliente**: Enviar respuestas y actualizaciones automáticas.

## 2. Arquitectura y Componentes Clave

El sistema se organiza en varios módulos dentro del `backend`:

-   **`ai_orchestrator.py` (Núcleo)**: Es el cerebro del sistema. La función `process_incoming_text` recibe todos los avisos y coordina las llamadas a los demás componentes para procesarlos.

-   **`llm.py`**: Contiene la lógica para interactuar con el modelo de lenguaje (Gemini). Define los *prompts* estructurados para tareas específicas (triage, extracción de datos) y maneja las llamadas a la API.

-   **`rules_engine.py`**: Implementa las políticas de negocio. Decide si un ticket debe auto-asignarse o qué plantilla de respuesta usar según la prioridad o el tipo de cliente.

-   **`similarity.py`**: Contiene la lógica para detectar si un aviso nuevo es un duplicado de uno reciente, basándose en la similitud del texto.

-   **`assignment.py`**: Implementa la heurística para sugerir al técnico o autónomo más adecuado para un trabajo, basándose en su especialidad, carga de trabajo actual, etc.

-   **`jobs_sla.py`**: Define un trabajo programado (`cron job`) que se ejecuta periódicamente para monitorizar los SLAs (Acuerdos de Nivel de Servicio) de los tickets abiertos, generando eventos de advertencia o incumplimiento.

-   **`normalizers.py` / `kpis.py`**: Módulos de utilidad para limpiar datos (ej. números de teléfono) y realizar cálculos (ej. estimar la fecha de vencimiento de un SLA).

-   **`ai_endpoints.py`**: Expone rutas API para que la interfaz de usuario (frontend) pueda interactuar con la IA (ej. solicitar una reasignación, sugerir una respuesta).

## 3. Flujo de Datos

1.  Un mensaje de **WhatsApp** llega al `whatsapp_webhook.py`.
2.  El webhook llama a `ai_orchestrator.process_incoming_text()`.
3.  El orquestador identifica al **cliente** (o lo crea con ayuda del LLM).
4.  Se realiza el **triage** del mensaje usando el LLM para obtener tipo, prioridad y título.
5.  El motor de **similitud** comprueba si es un duplicado.
6.  Si no es duplicado, se crea un nuevo **ticket** en la base de datos.
7.  El motor de **reglas** decide si el ticket se auto-asigna.
8.  El motor de **asignación** sugiere un técnico.
9.  Se actualiza el ticket con el técnico asignado (si aplica).
10. Se envía una **respuesta automática** al cliente vía WhatsApp.
11. Todas las operaciones de la IA y las comunicaciones se registran en las tablas `ai_logs` y `whatsapp_logs`.

## 4. Modelo de Datos

Se han añadido las siguientes tablas para dar soporte a este sistema:

-   **`ai_logs`**: Almacena un registro detallado de cada decisión tomada por la IA, incluyendo la entrada, la salida y el ticket asociado. Es fundamental para la depuración y la auditoría.
-   **`sla_events`**: Guarda los eventos relacionados con los SLAs, como advertencias de vencimiento o incumplimientos.

Además, la tabla `tickets` se ha ampliado con las siguientes columnas:

-   `source`: Origen del ticket (ej. 'whatsapp').
-   `prioridad`: Prioridad calculada por la IA (ej. 'alta', 'media', 'baja').
-   `sla_due`: Fecha y hora límite para cumplir el SLA.
-   `asignado_a`: ID del usuario (técnico) asignado.

## 5. Configuración y Variables de Entorno

-   **`GEMINI_API_KEY`**: Clave de la API para Google Gemini. Si no se proporciona o se establece como "demo", el sistema utilizará respuestas simuladas (`mock`) para no realizar llamadas reales, permitiendo el desarrollo y las pruebas sin coste.
-   **`WHATSAPP_DRY_RUN`**: Si se establece en `1`, el `WhatsAppClient` no enviará mensajes reales, sino que los registrará en la consola. Esto es ideal para el desarrollo local.

## 6. Pruebas

El fichero `tests/test_orchestrator.py` contiene pruebas unitarias y de integración para el flujo principal. Estas pruebas utilizan `monkeypatch` para simular las respuestas de la IA y del cliente de WhatsApp, garantizando que las pruebas sean rápidas, predecibles y no dependan de servicios externos.
