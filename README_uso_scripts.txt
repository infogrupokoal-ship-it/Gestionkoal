
GUÍA RÁPIDA — Scripts .BAT para C:\proyecto\gestion_avisos
==========================================================

1) Copia todos los .BAT a la raíz del proyecto: C:\proyecto\gestion_avisos

2) Orden típico de uso:
   - 00_setup_venv.bat      -> Crea/actualiza venv e instala requirements.
   - 02_run_dev.bat         -> Arranca en desarrollo (http://127.0.0.1:5000).
   - 03_run_prod_waitress.bat-> Arranca con Waitress en 8000 (más parecido a prod).
   - 04_init_db.bat         -> Ejecuta 'flask --app %FLASK_APP% init-db' (si existe).
   - 06_restart_local.bat   -> Mata el puerto 5000 y relanza dev.
   - 05_update_requirements.bat -> Congela dependencias.
   - 10_render_git_deploy.bat   -> git add/commit/push para Render.
   - 11_render_trigger_redeploy.bat -> Llama al Deploy Hook de Render (pon tu URL).

3) Si NO detecta FLASK_APP automáticamente:
   - Edita 01_detect_flask_app.bat o 02_run_dev.bat y añade por ejemplo:
       set FLASK_APP=backend:create_app
     Alternativas comunes:
       set FLASK_APP=app:create_app
       set FLASK_APP=backend:app
       set FLASK_APP=app:app

4) Errores comunes y soluciones:
   - "Fatal error in launcher: Unable to create process ...": 
       Ejecuta 00_setup_venv.bat y luego siempre activa el venv desde los .BAT.
   - "ModuleNotFoundError" (no encuentra tu paquete):
       Asegúrate de estar en la raíz del repo y que exista __init__.py en el paquete.
   - Puerto ocupado (5000/8000):
       Usa 06_restart_local.bat o cambia el puerto en 02_run_dev.bat/03_run_prod_waitress.bat.
   - En Render:
       - Procfile o render.yaml deben apuntar al módulo correcto.
       - Usa 10_render_git_deploy.bat para subir cambios o 11_render_trigger_redeploy.bat
         poniendo tu Deploy Hook URL.
