#!/bin/bash

echo "=============================================="
echo "  MLB Bot - Update Script"
echo "=============================================="
echo ""

# Configuracion
APP_DIR="/opt/mlb-bot"
PROJECT_NAME="mlb-bot"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar si es root
if [ "$EUID" -ne 0 ]; then
    log_error "Este script debe ejecutarse como root"
    exit 1
fi

# Navegar al directorio
cd $APP_DIR || {
    log_error "No se encontró el directorio $APP_DIR"
    exit 1
}

log_info "Directorio actual: $(pwd)"

# Obtener cambios de GitHub
log_info "Obteniendo últimos cambios de GitHub..."
git pull origin main

if [ $? -ne 0 ]; then
    log_error "Error al obtener cambios de GitHub"
    exit 1
fi

log_info "Cambios obtenidos exitosamente"

# Detener contenedores anteriores
log_info "Deteniendo contenedores anteriores..."
docker-compose down

# Reconstruir y iniciar
log_info "Reconstruyendo imagen y iniciando servicios..."
docker-compose up -d --build

# Esperar a que arranquen
log_info "Esperando a que arranquen los servicios..."
sleep 15

# Ver logs
log_info "Logs recientes del MLB Bot:"
docker logs mlb-bot_mlb-bot_1 --tail 20 2>&1 || docker service logs ${PROJECT_NAME}_mlb-bot --tail 20

echo ""
log_info "=============================================="
log_info "  Update completado!"
log_info "=============================================="
echo ""
echo "Comandos útiles:"
echo "  Ver logs: docker logs mlb-bot_mlb-bot_1 -f"
echo "  Ver estado: ./status.sh"
