#!/bin/bash

echo "=============================================="
echo "  MLB Bot - Update Script"
echo "=============================================="
echo ""

# Configuracion
APP_DIR="/opt/mlb-bot"
SERVICE_NAME="mlb-bot"

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

# Reconstruir y actualizar servicios
log_info "Reconstruyendo servicios con Docker Swarm..."

# Actualizar la imagen
docker build -t mlb-bot:latest .

# Actualizar el stack
log_info "Actualizando stack..."
docker stack deploy -c docker-compose.yml $SERVICE_NAME

# Esperar a que se actualicen
log_info "Esperando actualización..."
sleep 10

# Ver logs
log_info "Logs recientes del MLB Bot:"
docker service logs ${SERVICE_NAME}_mlb-bot --tail 15

echo ""
log_info "=============================================="
log_info "  Update completado!"
log_info "=============================================="
echo ""
echo "Comandos útiles:"
echo "  Ver logs: docker service logs ${SERVICE_NAME}_mlb-bot -f"
echo "  Ver estado: ./status.sh"
