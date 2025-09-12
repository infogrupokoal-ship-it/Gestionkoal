# Estado del Proyecto: Aplicación de Gestión de Servicios Grupo Koal

## 1. Objetivos del Proyecto:
El objetivo principal es desarrollar una aplicación integral de "Gestión de Servicios" (Gestión de Avisos) basada en Flask para Grupo Koal. Las características clave incluyen:
- Gestión de Clientes (CRUD: Crear, Leer, Actualizar, Eliminar)
- Gestión de Trabajos (CRUD)
- Catálogo de Servicios (CRUD)
- Gestión de Inventario (CRUD y Movimientos)
- Panel de Control Interactivo con integración de FullCalendar
- Autenticación de Usuarios y Control de Acceso Basado en Roles
- Registro de Actividad (Audit Trail)
- Módulo de Inventario Mejorado (Unidad de Medida, Autocompletado)
- Gestión de Autónomos/Colaboradores

## 2. Estado Actual y Próximos Pasos:

### Resumen:
Actualmente, estamos trabajando en la implementación de datos de ejemplo y la creación de botones "Rellenar Ejemplo" en los formularios para facilitar la comprensión del usuario. Hemos encontrado algunos problemas de ejecución relacionados con la configuración del entorno y la compatibilidad de la base de datos.

### Próximos Pasos Inmediatos:
1.  **Resolver el `NameError: name 'is_sqlite' is not defined`:** Este es el error actual que impide la inicialización de la base de datos.
2.  **Implementar botones "Rellenar Ejemplo" (página por página):**
    *   Formulario de Clientes (`templates/clients/form.html`) - **Completado.**
    *   Formulario de Proveedores (`templates/proveedores/form.html`) - **Completado.**
    *   Formulario de Materiales (`templates/materials/form.html`) - **Completado.**
    *   Formulario de Servicios (`templates/services/form.html`) - **Completado.**
    *   Formulario de Trabajos (`templates/trabajos/form.html`) - **Pendiente de corregir el error de `replace` y añadir el script.**
    *   Formulario de Tareas (`templates/tareas/form.html`) - **Pendiente.**
3.  **Verificar la aplicación:** Una vez que los errores de inicialización y los botones de ejemplo estén funcionando, se ejecutará la aplicación para asegurar su correcto funcionamiento.
4.  **Revisar y Refactorizar:** Después de que la aplicación esté operativa, se buscarán oportunidades de mejora y refactorización del código.

## 3. Registro Detallado de Errores Recientes:

### Error 1: `ModuleNotFoundError: No module named 'psycopg2'`
-   **Causa:** La librería `psycopg2`, necesaria para la conectividad con la base de datos PostgreSQL, no estaba instalada en el entorno.
-   **Intento de Solución:** Se añadió `psycopg2-binary` a `requirements.txt` y se intentó `pip install -r requirements.txt`.

### Error 2: `ERROR: Failed building wheel for psycopg2-binary` / `error: Microsoft Visual C++ 14.0 or greater is required.`
-   **Causa:** La instalación de `psycopg2-binary` falló debido a una dependencia del sistema (`Microsoft Visual C++ Build Tools`) que faltaba en la máquina Windows del usuario.
-   **Intento de Solución:** Se cambió de `psycopg2-binary` a `psycopg2` en `requirements.txt` (también falló con el mismo error). Se decidió continuar solo con SQLite por ahora y se comentaron las importaciones y el código relacionado con `psycopg2` en `app.py`.

### Error 3: `NameError: name '_execute_sql' is not defined` (Primera ocurrencia)
-   **Causa:** La función auxiliar `_execute_sql` se definió localmente dentro de `init_db_command` pero se estaba llamando desde `setup_new_database` (una función separada), lo que la hacía inaccesible.
-   **Intento de Solución:** Se movió la función `_execute_sql` al ámbito global en `app.py`.

### Error 4: `IndentationError: unexpected indent`
-   **Causa:** Indentación incorrecta en `app.py` después de mover la función `_execute_sql`.
-   **Intento de Solución:** Se corrigió la indentación en `app.py` alrededor de la línea afectada.

### Error 5: `NameError: name 'is_sqlite' is not defined` (Error actual)
-   **Causa:** La función `_execute_sql`, después de ser movida al ámbito global, perdió el acceso a la variable `is_sqlite`, que antes estaba disponible en el ámbito local de `init_db_command`.
-   **Intento de Solución:** El plan es modificar `_execute_sql` para que acepte `is_sqlite` como argumento y pasarlo en todas las llamadas. También, eliminar definiciones redundantes de `_execute_sql` dentro de `import_csv_data_command`.

### Error 6: Fallo repetido del comando `replace` en `templates/trabajos/form.html`
-   **Causa:** El `old_string` proporcionado al comando `replace` no coincide exactamente con el contenido del archivo, probablemente debido a múltiples ocurrencias de `{% endblock %}` o diferencias sutiles en el espaciado/saltos de línea.
-   **Intento de Solución:** Se intentó ser más específico con el `old_string` y se consideró reemplazar bloques más grandes o la función completa.

## 4. Entorno del Proyecto y Despliegue:

### Información del Servidor:
-   **Plataforma de Despliegue:** Render.com
-   **Problemas de Despliegue Conocidos:** Errores 404 persistentes en la ruta raíz, discrepancias entre el contenido local y el desplegado de `app.py` (sugiriendo problemas de caché o despliegue en Render). Problemas de conexión a la base de datos (`AttributeError: 'NoneType' object has no attribute 'fetchall'`) indicando problemas con la configuración de PostgreSQL de Render o el manejo de la cadena de conexión.

### Enlace de Acceso al Proyecto:
-   **URL de Despliegue en Render:** [Por favor, inserta aquí la URL real de tu proyecto en Render.com si está disponible.]

### Herramientas y Tecnologías:
-   **Backend:** Flask (Python)
-   **Base de Datos:** PostgreSQL (en Render), SQLite (para desarrollo local y como fallback actual)
-   **Frontend:** HTML, CSS, JavaScript (con plantillas Jinja2)
-   **Control de Versiones:** Git
-   **Gestor de Paquetes:** pip

## 5. Datos de Ejemplo Utilizados en `init-db` (Prefijo "ejem."):

### Credenciales de Inicio de Sesión (Ejemplo):
-   **Usuario:** `admin`
-   **Contraseña:** `admin_password` (¡Solo para desarrollo y pruebas! No usar en producción.)

### Ejemplo de Cliente:
-   **Nombre:** ejem. Maria Dolores
-   **Dirección:** Calle Maldiva, 24
-   **Teléfono:** 666555444
-   **Email:** ejemplo@email.com

### Ejemplo de Proveedor:
-   **Nombre:** ejem. Ferreteria La Esquina
-   **Persona de Contacto:** Juan Perez
-   **Teléfono:** 960000000
-   **Email:** info@ferreteria.com
-   **Dirección:** Calle de la Ferreteria 1, Valencia
-   **Tipo:** Ferreteria

### Ejemplo de Material:
-   **Nombre:** ejem. Martillo (Hammer)
-   **Descripción:** Martillo de carpintero (Carpenter's hammer)
-   **Stock Actual:** 10
-   **Precio Unitario:** 15.00
-   **Precio Recomendado:** 18.00
-   **Último Precio Vendido:** 14.00

### Ejemplo de Servicio:
-   **Nombre:** ejem. Fontaneria (Plumbing)
-   **Descripción:** Instalacion de grifo (Faucet installation)
-   **Precio:** 50.00
-   **Precio Recomendado:** 55.00
-   **Último Precio Vendido:** 48.00

### Ejemplo de Trabajo:
-   **Título:** ejem. Reparacion de persiana (ejem. Shutter repair)
-   **Descripción:** La persiana del dormitorio no baja (The bedroom shutter does not go down)
-   **Estado:** Pendiente
-   **Presupuesto:** 100.00
-   **Tasa de IVA:** 21.0
-   **Calificación de Dificultad:** 2

### Ejemplo de Tarea:
-   **Título:** ejem. Comprar lamas (Buy slats)
-   **Descripción:** Comprar lamas de persiana (Buy shutter slats)
-   **Estado:** Pendiente
-   **Método de Pago:** Efectivo
-   **Estado de Pago:** Pendiente
-   **Monto Abonado:** 0.00

## 6. Acceso al Código y Fuentes:
El código del proyecto se encuentra en el directorio local `C:\Users\info\OneDrive\Escritorio\gestion_avisos` y es accesible para su modificación.

---
