@echo off
call .venv\Scripts\activate
python test_integridad.py
if %errorlevel% neq 0 (
  echo ❌ Falló la validación previa al deploy
  exit /b 1
)
echo ✅ Validación completada con éxito
python run.py
