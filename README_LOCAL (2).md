# KOAL – Guía Local (Arranque + Git + IA Gemini)

## 🗂 Proyecto
- Carpeta: `C:\proyecto\gestion_avisos`
- Repo GitHub: `https://github.com/infogrupokoal-ship-it/Gestionkoal.git`

---

## 🚀 Instalación inicial (solo 1ª vez en este PC)
```powershell
cd C:\proyecto\gestion_avisos
python -m venv .venv
.venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
$Env:FLASK_APP="app.py"
flask init-db
```

---

## ▶️ Arranque diario (tras reiniciar)
**Opción A – Producción local (estable, como Render):**
- Doble clic: `start_local_fixed.bat`
- Equivalente manual:
  ```powershell
  cd C:\proyecto\gestion_avisos
  .venv\Scripts\activate.bat
  python run_waitress.py
  ```

**Opción B – Desarrollo (autoreload, ideal si la IA edita):**
- Doble clic: `start_dev_fixed.bat`
- Equivalente manual:
  ```powershell
  cd C:\proyecto\gestion_avisos
  .venv\Scripts\activate.bat
  $Env:FLASK_APP="app.py"
  $Env:FLASK_ENV="development"
  if (!(Test-Path "database.db")) { flask init-db }
  flask run
  ```

Abrir en navegador: `http://127.0.0.1:5000`

---

## 🤖 Trabajo con IA local (Gemini)
### 1) Mensaje de arranque recomendado (pégalo al abrir la IA)
```
Trabaja exclusivamente en C:\proyecto\gestion_avisos.
Edita solo app.py, templates\, static\, schema.sql y requirements.txt.
No toques .venv\, uploads\ ni database.db.
Usa siempre ? como placeholder SQL; las llamadas deben ir por _execute_sql(..., is_sqlite=is_sqlite).
Si el servidor está en waitress, avísame que debo reiniciarlo; si está en flask run, debería autorecargar.
Resume tus cambios con rutas y líneas afectadas.
```

### 2) Antes de cambios grandes (airbag)
```powershell
git add -A
git commit -m "Checkpoint antes de cambios IA"
```

### 3) Después de cambios que funcionan
```powershell
git add -A
git commit -m "Mejora IA: <describe cambio>"
git push
```

---

## ⬆️ Subir cambios a GitHub (cuándo y cómo)
**Cuándo**: al final del día, antes de deploy, tras arreglar algo que funciona, o antes de probar algo arriesgado.  
**Cómo**:
```powershell
cd C:\proyecto\gestion_avisos
git status
git add -A
git commit -m "Mensaje claro del cambio"
git push
```
Si el remoto no está configurado (solo 1 vez):
```powershell
git remote add origin https://github.com/infogrupokoal-ship-it/Gestionkoal.git
git branch -M main
git push -u origin main
```

**.gitignore recomendado**
```
.venv/
database.db
uploads/
__pycache__/
*.pyc
```

---

## ☁️ Despliegue Render (SQLite + Disk)
1. Conectar repo GitHub → New Web Service.
2. Build: `pip install -r requirements.txt`
3. Start: `python run_waitress.py`
4. Disk: montado en `/var/data`
5. Env vars:
```
DB_PATH=/var/data/database.db
UPLOAD_FOLDER=/var/data/uploads
```
6. Tras primer deploy (Shell de Render):
```
FLASK_APP=app.py flask init-db
```

---

## 🛠️ Solución rápida de problemas
- **No arranca**: venv activo, deps instaladas, `FLASK_APP=app.py`, ejecuta en la carpeta del proyecto.
- **Login falla**: usa usuarios de ejemplo (`password123`) o reemplaza `app.py` por el corregido.
- **Cambios IA no se aplican**: si estás con waitress, reinicia; con flask run, espera el autoreload.
- **psycopg2 error en Windows**: no lo uses en local. En Render/Postgres usa `psycopg2-binary`.
