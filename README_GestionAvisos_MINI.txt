# Gestión de Avisos — Paquete mínimo y cómo usarlo

## ¿Qué archivos me quedo?
- `render.yaml` → (ÚNICO archivo de despliegue en Render). **Elimina duplicados** como `render (1).yaml`.
- `requirements.txt` → Dependencias (si no lo tienes, créalo).
- Código fuente de tu app (por ejemplo `backend/` con `__init__.py` y `create_app()`).
- `start_local.bat`, `init_db.bat`, `run_dev.bat` → Atajos en Windows para desarrollar.
- `.gitignore` → Para no subir basura al repo.
- (Opcional) `Procfile` → **No es necesario si usas `render.yaml`**, elige uno u otro. Recomiendo **solo `render.yaml`**.

## ¿Qué puedo borrar?
- Duplicados: `render (1).yaml`.
- Backups: `app.py.bak_20250913` (mejor integrar sus cambios en el código y borrar el backup).
- `logtail.ps1` → Solo necesario si **tú** lo usas para logs; si no, bórralo.
- `database.db` → No lo subas al repo; se genera en runtime. Déjalo ignorado por `.gitignore`.

## Cómo trabajar en LOCAL (Windows)
1) Abre PowerShell o CMD en la carpeta del proyecto.
2) Ejecuta una vez:
   ```
   start_local.bat
   ```
   Si tu factoría de Flask NO es `backend:create_app`, pásala:
   ```
   start_local.bat app:create_app
   ```
3) Inicializa la base de datos (si tu app tiene comando `init-db`):
   ```
   init_db.bat
   ```
4) Arranca en desarrollo:
   ```
   run_dev.bat
   ```
   Abre http://127.0.0.1:5000

## Cómo desplegar en Render
- Mantén **solo `render.yaml`** en el repo (recomendado).
- El servicio usará:
  ```
  gunicorn "backend:create_app()"
  ```
  Cambia el módulo/fábrica si es distinto (por ejemplo `"app:create_app()"`).

## Variables importantes
- `APP_MODULE` → Módulo y fábrica de Flask. Por defecto `backend:create_app`.
- Si cambias tu estructura, úsalo como argumento en los `.bat`:
  - `start_local.bat app:create_app`
  - `init_db.bat app:create_app`
  - `run_dev.bat app:create_app`

## Estructura mínima sugerida
```
/proyecto
  backend/
    __init__.py        # define create_app()
    routes.py          # tus rutas
    models.py          # tus modelos
  requirements.txt
  render.yaml          # despliegue en Render (elige este en vez de Procfile)
  .gitignore
  start_local.bat
  init_db.bat
  run_dev.bat
```

## Notas rápidas
- El error de Flask "Unable to create process..." suele ser por mezclar rutas de venv. Soluciona con estos `.bat`:
  - Crea y activa SIEMPRE `venv` local del proyecto con `start_local.bat` antes de ejecutar `flask`.
- Si `flask --app backend:create_app init-db` falla, revisa:
  - Que `backend/__init__.py` tenga una función `create_app()` que registre el CLI `init-db`.
  - Que estés **dentro del venv** (verás `(venv)` en el prompt).
