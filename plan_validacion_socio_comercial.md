
# ✅ Plan de Validación Completa en Staging / Producción

## 🎯 Objetivo
Verificar que la funcionalidad de **"Socio Comercial"** está correctamente integrada y que el sistema se comporta de forma esperada desde el punto de vista de cada tipo de usuario (Admin, Comercial, Autónomo).

---

## 1. 🧪 Preparación del Entorno

- [ ] El entorno de staging está actualizado con el código más reciente.
- [ ] La base de datos se ha inicializado con `schema.sql` y contiene datos de prueba para:
  - Al menos 2 socios comerciales.
  - Al menos 2 clientes, uno con y otro sin socio comercial.
  - Al menos 2 trabajos (tickets) con distintas combinaciones de asignación.
- [ ] Existen usuarios de prueba para los siguientes roles:
  - Admin
  - Comercial A
  - Comercial B
  - Autónomo

---

## 2. 👤 Pruebas por Rol

### 2.1 Admin

- [ ] Puede ver **todos los clientes**.
- [ ] Puede ver **todos los trabajos y presupuestos**.
- [ ] Puede acceder al **reporte de comisiones** y ver todas las comisiones generadas.
- [ ] Puede **marcar comisiones como pagadas** desde la interfaz.
- [ ] Puede asignar "Socio Comercial" al crear/editar clientes o trabajos.
- [ ] Puede acceder a las **APIs** `/api/comisiones` y `/api/trabajos` y ver todos los datos.
- [ ] El dashboard muestra KPIs globales.

### 2.2 Comercial

- [ ] Solo puede ver sus **clientes referidos**.
- [ ] Solo puede ver sus **trabajos** (trabajos donde es el `comercial_id`).
- [ ] Puede ver **sus comisiones** en el menú "Mis Comisiones".
- [ ] No puede ver o editar comisiones de otros socios.
- [ ] El dashboard solo muestra trabajos y métricas **de sus clientes**.
- [ ] El autocompletado de clientes solo muestra **clientes propios**.
- [ ] En la tabla de trabajos, clientes, presupuestos y comisiones, se muestra correctamente su nombre como "Socio Comercial".

### 2.3 Autónomo

- [ ] Puede acceder únicamente a las tareas asignadas.
- [ ] No puede ver comisiones ni clientes.
- [ ] No tiene acceso a los dashboards ni reportes.

---

## 3. 🔗 Pruebas de Flujo Completo

- [ ] Crear un cliente con socio comercial asignado.
- [ ] Crear un trabajo para ese cliente y confirmar que **hereda automáticamente el socio comercial**.
- [ ] Confirmar que se **genera una comisión** al cerrar el trabajo (si corresponde).
- [ ] Verificar que el socio comercial ve esa comisión.
- [ ] Marcar la comisión como pagada desde un usuario admin.
- [ ] Confirmar que el estado de la comisión cambia correctamente.
- [ ] Editar un cliente y cambiar su socio comercial.
- [ ] Editar un trabajo y cambiar el socio comercial (si el usuario tiene permiso).

---

## 4. 🖼️ Revisión Visual y UX

- [ ] Verificar que el término **"Socio Comercial"** aparece de forma consistente en todas las vistas.
- [ ] Revisar responsividad en móvil/tablet (scroll en tablas largas).
- [ ] Confirmar que los formularios tienen los permisos correctos (visibilidad condicional).
- [ ] Revisar mensajes de éxito/error al guardar, asignar socios, marcar comisiones como pagadas, etc.

---

## 5. 📡 Pruebas de API

- [ ] `GET /api/comisiones` devuelve:
  - Solo comisiones propias para socios.
  - Todas las comisiones para admin.
- [ ] `GET /api/trabajos` devuelve:
  - Solo trabajos propios para socios.
  - Todos los trabajos para admin.
- [ ] Autocompletado de clientes filtra según el rol.
- [ ] Endpoints de analytics filtran correctamente por comercial_id si aplica.

---

## 6. 🔒 Validación de Seguridad

- [ ] Un socio comercial **no puede acceder** a los recursos de otros (comprobado por URL directa).
- [ ] Un usuario no autenticado no puede acceder a `/comisiones`, `/api/comisiones`, `/dashboard`, etc.
- [ ] Los permisos `has_permission` funcionan correctamente para `manage_commissions`, `assign_commercial_partner`, etc.

---

## 7. 📋 Revisión Técnica

- [ ] El archivo `schema.sql` contiene las siguientes columnas/tablas:
  - `clientes.referred_by_partner_id`
  - `tickets.comercial_id`
  - `presupuestos.comercial_id`
  - Tabla `comisiones` completa.
- [ ] El archivo ha sido validado con SQLite (puedes usar el comando:  
  ```bash
  sqlite3 database.db ".read schema.sql"
  ```)
- [ ] No hay errores de migración ni duplicados de campos.

---

## 8. 🔍 Monitoreo y Logs

- [ ] Revisar logs en Render para detectar errores tras el despliegue.
- [ ] Validar que no hay errores 500 tras crear, editar o listar clientes, trabajos o comisiones.
- [ ] Si usas herramientas como Sentry o LogRocket, confirmar que capturan correctamente los eventos.

---

## 9. ✅ Checklist Final

- [ ] Todos los roles fueron probados.
- [ ] Todos los flujos críticos fueron completados sin error.
- [ ] Todo se visualiza correctamente en desktop y móvil.
- [ ] Las APIs funcionan como se espera.
- [ ] El estado del sistema es coherente con la lógica de negocio definida.
