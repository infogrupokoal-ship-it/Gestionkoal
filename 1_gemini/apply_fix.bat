@echo off
echo [FIX SCRIPT] Copiando el archivo backend\jobs.py corregido...

copy /Y "C:\proyecto\gestion_avisos\1_gemini\analysis\jobs_fixed.py.txt" "C:\proyecto\gestion_avisos\backend\jobs.py"

if %errorlevel% == 0 (
    echo.
    echo [SUCCESS] El archivo jobs.py se ha actualizado correctamente.
) else (
    echo.
    echo [ERROR] No se pudo copiar el archivo. Por favor, revisa los permisos.
)

echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause > nul
