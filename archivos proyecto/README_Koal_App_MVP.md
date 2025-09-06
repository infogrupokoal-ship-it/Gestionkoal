# Grupo Koal – MVP Operativo (Gestión de avisos, WhatsApp, técnicos y almacén)

Fecha: 2025-08-30

Este paquete contiene:

- `whatsapp_templates_es_val.md` – Plantillas para WhatsApp Business (ES/VAL), listas para solicitar aprobación en Meta.
- Carpeta `checklists/` – CSVs con listas de verificación para servicios clave (instalación/mantenimiento split, cassette, VRV, verticales/PRL, impermeabilización).
- `schema_grupokoal.sql` – Esquema de base de datos (PostgreSQL) con entidades: clientes, direcciones, equipos, avisos/tickets, partes, materiales/stock, herramientas/préstamos, presupuestos/facturas, RGPD, auditoría.
- `api_mvp_postman.json` – Colección Postman con endpoints para: tickets, eventos, materiales/stock, WhatsApp webhook/envío de plantillas, presupuestos/facturas y préstamos de herramientas.
- `automations_zapier_make.md` – Flujos de automatización (lead→ticket, cita, recordatorios, reseñas, OCR proveedores→stock).
- `material_catalogo.csv` – Estructura de catálogo base (SKU, EAN, nombre, ubicación, stock mínimo).
- `herramientas_qr.csv` – Estructura de préstamos de herramientas por QR.
- `roles_permisos.csv` – Roles sugeridos y ámbitos de permiso.

> Nota legal: revisa RGPD/LOPDGDD con tu asesor. Las plantillas incluyen texto de consentimiento básico y opción de baja por WhatsApp.
