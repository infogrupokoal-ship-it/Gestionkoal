# Script para configurar y ejecutar el entorno de desarrollo local en PowerShell.

# Salir inmediatamente si un comando falla
$ErrorActionPreference = "Stop"

# --- Colores para la salida ---
$GREEN = "`e[32m"
$YELLOW = "`e[93m"
$NC = "`e[0m" # No Color

# 1. Crear entorno virtual si no existe
if (-not (Test-Path ".venv")) {
    Write-Host "${YELLOW}Creando entorno virtual en ./.venv...${NC}"
    python -m venv .venv
} else {
    Write-Host "${GREEN}Entorno virtual ./.venv ya existe.${NC}"
}

# 2. Activar entorno virtual
. ./.venv/Scripts/Activate.ps1

# 3. Instalar/actualizar dependencias
Write-Host "${YELLOW}Instalando/actualizando dependencias desde requirements.txt...${NC}"
pip install -U pip wheel
pip install -r requirements.txt

# 4. Cargar variables de entorno si .env.local existe
if (Test-Path ".env.local") {
    Write-Host "${GREEN}Cargando variables de entorno desde .env.local...${NC}"
    Get-Content .env.local | ForEach-Object {
        if ($_ -match '=' -and -not $_.StartsWith('#')) {
            $key, $value = $_.Split('=', 2)
            [System.Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim())
        }
    }
} else {
    Write-Host "${YELLOW}ADVERTENCIA: .env.local no encontrado. Usando valores por defecto.${NC}"
}

# 5. Aplicar migraciones de base de datos
Write-Host "${YELLOW}Aplicando migraciones de base de datos (flask db upgrade)...${NC}"
flask db upgrade

# 6. Sembrar datos iniciales
Write-Host "${YELLOW}Sembrando datos iniciales (flask seed)...${NC}"
flask seed

# 7. Iniciar la aplicación
Write-Host "${GREEN}Iniciando servidor de desarrollo en http://127.0.0.1:5000...${NC}"
flask run --host=127.0.0.1 --port=5000
