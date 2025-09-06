# Project Checkpoint: Grupo Koal Service Management App

This document summarizes the current state of the "Grupo Koal Service Management App" development as of this checkpoint.

## 1. Implemented Features (Modules 1, 2, 6 - Core Management, Dashboard, User Auth)

*   **Basic Flask Application:** Core web application structure using Flask.
*   **Database Persistence (SQLite):** Data is stored in `database.db` using SQLite.
*   **Database Schema (`schema.sql`):** Defines `clients`, `trabajos`, `services`, `materials`, `stock_movements`, `users`, `roles`, `user_roles` tables.
*   **Logo Integration:** Grupo Koal logo displayed in the header (now larger).
*   **Client Management (CRUD):**
    *   Add, view, edit, and delete client records.
    *   Fields: Name, Address, Phone, WhatsApp, Email.
*   **Job Management (CRUD):**
    *   Add, view, edit, and delete job records.
    *   Jobs are linked to clients.
    *   Fields: Title, Description, Status (Pendiente, En Progreso, Presupuestado, Finalizado), Budget, Visit Date.
*   **Service Catalog (CRUD):**
    *   Add, view, edit, and delete services.
    *   Fields: Name, Description, Price.
*   **Inventory Management (CRUD & Movements):**
    *   Add, view, edit, and delete materials.
    *   Fields: Name, Description, Current Stock, Unit Price, Min Stock Level.
    *   Record stock movements (IN/OUT) which update `current_stock`.
*   **Interactive Dashboard:**
    *   New main page (`/`).
    *   Displays key statistics (Pendientes, En Progreso, Finalizados, Presupuestados).
    *   **FullCalendar Integration:** Interactive calendar displaying jobs by visit date.
        *   Events are color-coded by job status.
        *   Clicking an event navigates to the job edit page.
        *   Calendar is localized to Spanish.
    *   **Upcoming Jobs List:** Displays the next 3 upcoming jobs.
*   **User Authentication and Roles:**
    *   Login/Logout functionality.
    *   Default admin user created (`admin`/`admin_password`).
    *   All existing pages are now protected and require login.
    *   New "Usuarios" section for managing users and roles (Admin, Oficinista, Autonomo).
*   **Flash Messages:** User feedback messages for successful operations.

## 2. Key Files and Their Roles

*   `app.py`: Main Flask application logic, defines routes, handles database interactions, and renders templates. **(Updated with User Auth, Inventory, Services, Dashboard logic)**
*   `schema.sql`: SQL script for creating all database tables (`clients`, `trabajos`, `services`, `materials`, `stock_movements`, `users`, `roles`, `user_roles`).
*   `templates/base.html`: Base Jinja2 template, includes common HTML structure, header, logo, navigation (now with Users, Materials, Services links), FullCalendar library, and defines content/script blocks.
*   `templates/dashboard.html`: The new main dashboard page with stats, upcoming jobs list, and the FullCalendar instance.
*   `templates/trabajos/list.html`: List view of all jobs (accessible via `/trabajos`).
*   `templates/trabajos/form.html`: Form for adding and editing job details.
*   `templates/clients/list.html`: List view of all clients (accessible via `/clients`).
*   `templates/clients/form.html`: Form for adding and editing client details.
*   `templates/services/list.html`: List view of all services (accessible via `/services`).
*   `templates/services/form.html`: Form for adding and editing services.
*   `templates/materials/list.html`: List view of all materials (accessible via `/materials`).
*   `templates/materials/form.html`: Form for adding and editing materials.
*   `templates/stock_movements/form.html`: Form for recording stock movements.
*   `templates/login.html`: User login form.
*   `templates/register.html`: User registration form.
*   `templates/users/list.html`: List view of all users.
*   `templates/users/form.html`: Form for adding and editing user details.
*   `templates/editar.html`: (Legacy, can be removed or refactored if not used by new job edit flow)
*   `static/style.css`: Cascading Style Sheet for application's visual design. **(Updated for larger logo, dashboard, calendar, new sections)**
*   `static/logo.jpg`: Grupo Koal company logo.

## 3. Next Planned Features (Revised Plan)

The next features will focus on enhancing usability, data integrity, and accountability, building upon the User Authentication module.

*   **Módulo 7: Registro de Actividad (Audit Trail)**
    *   **Objetivo:** Registrar quién realiza cada acción importante en el sistema.
    *   **Funcionalidades:** Trazabilidad de acciones (creación, edición, eliminación) asociadas al usuario logueado.
    *   **Impacto en DB:** Nueva tabla `activity_log`.

*   **Módulo 8: Mejoras en el Módulo de Inventario**
    *   **Objetivo:** Mejorar la precisión y la eficiencia en la gestión de materiales.
    *   **Funcionalidades:**
        *   **Unidad de Medida (UoM):** Añadir campo `unit_of_measure` al material (texto libre inicialmente).
        *   **Autocompletado de Materiales:** Sugerir materiales existentes al escribir en el formulario de movimientos de stock.
    *   **Impacto en DB:** Modificación de la tabla `materials`.

*   **Módulo 5: Gestión de Autónomos/Colaboradores (Core)**
    *   **Objetivo:** Mantener un registro de los autónomos/colaboradores, sus especialidades y el estado de su documentación clave.
    *   **Funcionalidades:** Perfiles de autónomos, registro de documentación (Seguro RC, Curso PNL, etc.), alertas de vencimiento.
    *   **Impacto en DB:** Nuevas tablas `autonomos`, `specialties`, `autonomo_specialties`, `autonomo_documents`.

---
