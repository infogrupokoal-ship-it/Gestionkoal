
## 8. Procedimientos Intentados y Resultados (Incluyendo Fallos):

### 8.1. Intentos de Ejecución Local de la Aplicación Flask:

-   **Comando Intentado:** `flask run`
    -   **Resultado:** Falló con `"flask" no se reconoce como un comando interno o externo`.
    -   **Análisis:** `flask` no estaba en el PATH del sistema o el entorno virtual no estaba activado correctamente.
    -   **Acción Correctiva:** Se cambió a `python -m flask run`.

-   **Comando Intentado:** `python -m flask run` (después de `flask run`)
    -   **Resultado:** Falló con `ModuleNotFoundError: No module named 'psycopg2'`.
    -   **Análisis:** La librería `psycopg2` no estaba instalada en el entorno.
    -   **Acción Correctiva:** Se añadió `psycopg2-binary` a `requirements.txt` y se intentó `pip install -r requirements.txt`.

-   **Comando Intentado:** `pip install -r requirements.txt` (con `psycopg2-binary`)
    -   **Resultado:** Falló con `ERROR: Failed building wheel for psycopg2-binary` y `error: Microsoft Visual C++ 14.0 or greater is required.`.
    -   **Análisis:** `psycopg2-binary` requiere las herramientas de compilación de C++ de Microsoft Visual Studio en Windows para su instalación, las cuales no estaban presentes en el sistema del usuario.
    -   **Acción Correctiva:** Se intentó cambiar a `psycopg2` (versión no-binary) en `requirements.txt`, pero el resultado fue el mismo. Se decidió comentar temporalmente todo el código relacionado con `psycopg2` en `app.py` para permitir que la aplicación se ejecute con SQLite para el desarrollo local.

-   **Comando Intentado:** `python -m flask init-db` (después de mover `_execute_sql`)
    -   **Resultado:** Falló con `NameError: name '_execute_sql' is not defined`.
    -   **Análisis:** La función `_execute_sql` se movió al ámbito global, pero su definición original dentro de `init_db_command` no se eliminó completamente, causando una redefinición o un conflicto de alcance.
    -   **Acción Correctiva:** Se corrigió la indentación y se aseguró que `_execute_sql` estuviera definida solo una vez y en el ámbito global.

-   **Comando Intentado:** `python -m flask init-db` (después de corregir la indentación)
    -   **Resultado:** Falló con `NameError: name 'is_sqlite' is not defined`.
    -   **Análisis:** La función `_execute_sql` (ahora global) no recibía el parámetro `is_sqlite` que necesitaba para determinar el tipo de base de datos.
    -   **Acción Correctiva:** Se modificó la firma de `_execute_sql` para aceptar `is_sqlite` como argumento y se actualizaron todas las llamadas a `_execute_sql` para pasar este parámetro. También se eliminaron las definiciones redundantes de `_execute_sql` dentro de `import_csv_data_command`.

-   **Comando Intentado:** `replace` en `templates/trabajos/form.html` (para añadir el script de ejemplo)
    -   **Resultado:** Falló repetidamente con `Failed to edit, Expected 1 occurrence but found 2 for old_string`.
    -   **Análisis:** El `old_string` (`{% endblock %}`) no era lo suficientemente específico, ya que existían múltiples ocurrencias en el archivo.
    -   **Acción Correctiva:** Se intentará una estrategia de reemplazo más precisa, posiblemente utilizando un contexto más amplio para el `old_string` o identificando la ocurrencia exacta a reemplazar.

---
