# 🧠 PROMPT MAESTRO PARA GEMINI — AUDITORÍA INTEGRAL GESTIÓNKOAL

## 🔷 CONTEXTO GENERAL

Este proyecto es **GestiónKoal**, un sistema Flask + SQLite que integra:
- Gestión de **avisos, clientes, tickets y proveedores**.
- Panel web con **roles** (`admin`, `autonomo`, `oficina`, `cliente`, `proveedor`).
- Automatización de **avisos vía WhatsApp** y respuesta por **IA**.
- Control de **KPIs** y dashboard de tareas.
- Scripts `.bat` para desarrollo, producción local y Render.
- Un backend estable con **tests completos (pytest)** y un **modo DRY-RUN** para WhatsApp e IA.
- Integración futura con **Meta Cloud API** (WhatsApp Business real) y despliegue en **Render**.

El objetivo **NO** es simplificar, sino **hacerlo funcionar con todas las ideas integradas**, garantizando:
1. Coherencia total entre base de datos, backend, tests y WhatsApp.
2. Que la IA conteste automáticamente cuando llega un aviso real.
3. Que las notificaciones se guarden en la base de datos y se reflejen en el dashboard.
4. Que el despliegue en Render sea funcional y estable sin romper las dependencias.

---

## 🔶 MISIÓN PARA GEMINI

**Revisa, corrige y conecta todo el proyecto GestiónKoal sin eliminar contexto ni simplificar funcionalidades.**

Debe realizar las siguientes tareas **en orden**:

---

### 🧩 BLOQUE 1 – AUDITORÍA COMPLETA DEL PROYECTO

1. Revisar todos los archivos críticos:
   - `backend/__init__.py`
   - `backend/models.py`
   - `backend/auth.py`
   - `backend/metrics.py`
   - `backend/orchestrator.py`
   - `backend/whatsapp_meta.py`
   - `backend/whatsapp_twilio.py`
   - `backend/ai_orchestrator.py`
   - `schema.sql`
   - `temp_init_db.py`
   - `tests/` (especialmente `test_whatsapp.py`, `test_dashboard.py`, `test_kpis`)

2. Confirmar que **todas las tablas** existen en `schema.sql`:
   - `users`, `roles`, `user_roles`, `clientes`, `tickets`, `servicios`, `providers`, `materiales`,
     `ai_logs`, `whatsapp_logs`, `sla_events`, `notifications`.
   - Cada tabla debe tener **PK, created_at y FKs válidas**.

3. Verificar que `schema.sql` ejecuta en el orden correcto (**DROP → CREATE → SEED**)  
   y que la tabla `notifications` se crea y persiste.

4. Confirmar que los **roles iniciales** (`admin`, `autonomo`, `cliente`, `proveedor`, etc.) y los **usuarios de prueba** existen con IDs fijos.

---

### 🧠 BLOQUE 2 – BACKEND Y MODELOS

1. Asegurarse de que `backend/models.py` usa automap dinámico sin `Base` global.
2. Verificar que todas las rutas usan `get_db()` o `db.session` correctamente.
3. Comprobar que las funciones de IA (`ai_orchestrator.py`) registran cada interacción en `ai_logs` y `whatsapp_logs`.

---

### 💬 BLOQUE 3 – WHATSAPP + IA (DRY-RUN FUNCIONAL)

1. Validar que la variable `WHATSAPP_DRY_RUN=1` activa modo simulado.
2. Confirmar que `/webhooks/whatsapp/` procesa JSON real del webhook Meta.
3. Comprobar que, al recibir un mensaje:
   - Se crea un **cliente** si no existe.
   - Se crea un **ticket** asociado.
   - Se genera un **log de IA** con la respuesta.
   - Se imprime `[DRY-RUN] WA -> +34600111222: ...`.
   - Si `notifications` existe, se inserta ahí también.
4. Si `WHATSAPP_DRY_RUN=0`, debe enviar el mensaje real (modo producción).

---

### 📊 BLOQUE 4 – DASHBOARD Y MÉTRICAS

1. Confirmar que `/dashboard` carga con KPIs correctos.
2. Que los tests `test_dashboard_kpis.py` y `test_health.py` pasen.
3. Verificar que el endpoint `/api/dashboard/kpis` devuelve el JSON esperado con `ok: true`.

---

### 📦 BLOQUE 5 – DEPLOY Y ENTORNO

1. Revisar `Dockerfile` (usuario no-root, variable `$PORT`, `--no-cache-dir`).
2. Revisar `.dockerignore` para evitar logs y caches.
3. Revisar `render.yaml` para despliegue automático.
4. Verificar `start_prod_local.bat` o `start_render.bat` para producción local.

---

### 🧪 BLOQUE 6 – PRUEBAS Y VALIDACIÓN FINAL

1. Ejecutar `pytest -q --disable-warnings`.
2. Simular webhook con `curl` y payload desde fichero.
3. Verificar creación de cliente, ticket, logs y mensajes DRY-RUN.
4. Validar `/healthz` → `200 OK {"status":"ok","db":"ok"}`.

---

### ☁️ BLOQUE 7 – PREPARACIÓN RENDER

1. Confirmar que `render.yaml` apunta a `waitress-serve` y usa `FLASK_APP=backend:create_app`.
2. Que `requirements.txt` contenga `waitress`, `flask_sqlalchemy`, `pytest`, `requests`.
3. Simular build local (`docker build -t gestionkoal .`) y ejecución (`docker run -p 5000:5000 gestionkoal`).
4. Si todo pasa, preparar despliegue real en Render.

---

### ✅ BLOQUE 8 – INFORME FINAL

Gemini debe generar:
- Un **resumen técnico completo**:
  - Listado de tablas finales.
  - Estado de cada módulo.
  - Pruebas superadas.
  - Logs de IA simulada.
- Un **checklist de producción** para Render.
- Un **log de auditoría final** (qué cambió y por qué).

---

## ⚙️ VARIABLES DE ENTORNO REQUERIDAS

```
FLASK_APP=backend:create_app
FLASK_ENV=production
WHATSAPP_DRY_RUN=1
GEMINI_API_KEY=demo
GOOGLE_API_KEY=dummy
GOOGLE_CSE_ID=dummy
SENTRY_DSN=
```

---

## 🚀 OBJETIVO FINAL

El sistema debe:
- Aceptar un mensaje WhatsApp en `/webhooks/whatsapp/`.
- Crear cliente, ticket y notificación en BD.
- Registrar logs en `ai_logs` y `whatsapp_logs`.
- Devolver un mensaje DRY-RUN en consola.
- Mostrar métricas actualizadas en `/dashboard`.
- Pasar todos los tests.
- Estar listo para desplegar en Render sin fallos.