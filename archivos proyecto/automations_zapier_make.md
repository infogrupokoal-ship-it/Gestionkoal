# Automatizaciones (Zapier / Make)

## 1) Lead WhatsApp → Ticket
- **Trigger:** WhatsApp inbound con palabras clave ("avería", "presupuesto", "instalación").
- **Actions:** 
  1. Extraer datos (nombre, teléfono, dirección si viene).
  2. Crear `cliente` si no existe (buscar por teléfono).
  3. Crear `ticket` (tipo, prioridad por palabras clave).
  4. Responder con plantilla `koal_intake_datos_es`.
  5. Si hay enlace de calendario, enviar link de cita.

## 2) Web form / Wallapop → Ticket
- Trigger formulario (Web/Google Forms) o Wallapop webhook.
- Actions: Crear cliente + ticket, asignar a cola según zona/postal.

## 3) Aceptación presupuesto → Evento ejecución
- Trigger: respuesta "ACEPTO {{quote_id}}" en WhatsApp o botón en portal.
- Actions: Cambiar estado presupuesto, generar evento en la agenda del equipo y enviar confirmación.

## 4) Cierre técnico → Factura + Pago
- Trigger: evento `finalizado`.
- Actions: generar informe PDF + factura, crear link de pago (Stripe/RedSys) y enviarlo por WhatsApp (plantilla `koal_cierre_factura_es`).

## 5) Recordatorios de mantenimiento (estacional)
- Programado por zonas / tipo de equipo. Enviar `koal_mantenimiento_recordatorio_es` con botón de agendar.

## 6) Solicitud reseña
- Trigger: 48h tras cierre sin incidencias.
- Action: enviar `koal_solicitud_resena_es` con enlace a Google Maps.

## 7) OCR proveedores → Stock
- Trigger: email con factura proveedor (PDF).
- Action: OCR líneas, conciliar con `materiales` y crear `stock_movs` (compra).

## 8) Control de herramienta por QR
- Trigger: escaneo QR (salida/devolución).
- Action: crear `prestamos_herramienta` y alerta si > X días fuera.