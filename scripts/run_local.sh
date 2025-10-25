#!/bin/bash
# Script para configurar y ejecutar el entorno de desarrollo local.

# Salir inmediatamente si un comando falla
set -e

# --- Colores para la salida ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creando entorno virtual en ./.venv...${NC}"
    python -m venv .venv
else
    echo -e "${GREEN}Entorno virtual ./.venv ya existe.${NC}"
fi

# 2. Activar entorno virtual
source ./.venv/bin/activate

# 3. Instalar/actualizar dependencias
echo -e "${YELLOW}Instalando/actualizando dependencias desde requirements.txt...${NC}"
pip install -U pip wheel
pip install -r requirements.txt

# 4. Cargar variables de entorno si .env.local existe
if [ -f ".env.local" ]; then
    echo -e "${GREEN}Cargando variables de entorno desde .env.local...${NC}"
    export $(grep -v '^#' .env.local | xargs)
else
    echo -e "${YELLOW}ADVERTENCIA: .env.local no encontrado. Usando valores por defecto.${NC}"
fi

# 5. Aplicar migraciones de base de datos
echo -e "${YELLOW}Aplicando migraciones de base de datos (flask db upgrade)...${NC}"
flask db upgrade

# 6. Sembrar datos iniciales
echo -e "${YELLOW}Sembrando datos iniciales (flask seed)...${NC}"
flask seed

# 7. Iniciar la aplicación
echo -e "${GREEN}Iniciando servidor de desarrollo en http://127.0.0.1:5000...${NC}"
flask run --host=127.0.0.1 --port=5000
