#!/bin/bash

echo "=============================================="
echo "  MLB Bot - Deploy Script"
echo "=============================================="
echo ""

# Configuracion
APP_DIR="/opt/mlb-bot"
SERVICE_NAME="mlb-bot"
PORT=8000

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

# Verificar Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker no está instalado"
    exit 1
fi

# Verificar Docker Compose
if ! docker compose version &> /dev/null; then
    log_error "Docker Compose no está instalado"
    exit 1
fi

# Verificar Swarm
if [ ! -f /var/lib/docker/swarm/state.json ]; then
    log_info "Inicializando Docker Swarm..."
    docker swarm init
fi

# Navegar al directorio
cd $APP_DIR || {
    log_error "No se encontró el directorio $APP_DIR"
    log_info "Clonando repositorio..."
    cd /opt
    git clone https://github.com/xxsotoxx/mlb-bot.git
    cd $APP_DIR
}

log_info "Directorio actual: $(pwd)"

# Crear .env si no existe
if [ ! -f ".env" ]; then
    log_info "Creando archivo .env desde .env.example..."
    cp .env.example .env
    log_warn "=============================================="
    log_warn "IMPORTANTE: Edita el archivo .env y cambia el password"
    log_warn "Ejecuta: nano .env"
    log_warn "Luego ejecuta este script de nuevo"
    log_warn "=============================================="
    exit 1
fi

# Verificar archivos necesarios
if [ ! -f "docker-compose.yml" ]; then
    log_error "No se encontró docker-compose.yml"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    log_error "No se encontró requirements.txt"
    exit 1
fi

# Detener servicios anteriores si existen
log_info "Deteniendo servicios anteriores..."
docker stack rm $SERVICE_NAME 2>/dev/null
sleep 5

# Remover servicios antiguos
log_info "Limpiando servicios antiguos..."
docker service ls | grep $SERVICE_NAME && docker stack rm $SERVICE_NAME 2>/dev/null || true
sleep 3

# Deploy con Docker Swarm
log_info "Haciendo deploy con Docker Swarm..."
docker stack deploy -c docker-compose.yml $SERVICE_NAME

# Esperar a que arranquen los servicios
log_info "Esperando a que arranquen los servicios..."
sleep 10

# Verificar estado
log_info "Verificando estado de servicios..."
docker service ls

# Ver logs
log_info "Logs del MLB Bot:"
docker service logs ${SERVICE_NAME}_mlb-bot --tail 20

# Verificar si está corriendo
if docker service ls | grep -q ${SERVICE_NAME}_mlb-bot; then
    echo ""
    log_info "=============================================="
    log_info "  Deploy completado exitosamente!"
    log_info "=============================================="
    echo ""
    echo "La aplicación está disponible en:"
    echo "  http://localhost:$PORT"
    echo "  http://$(curl -s ifconfig.me):$PORT"
    echo ""
    echo "Comandos útiles:"
    echo "  docker service logs ${SERVICE_NAME}_mlb-bot -f"
    echo "  ./status.sh"
    echo "  ./update.sh"
else
    log_error "El deploy falló. Verifica los logs."
    docker service logs ${SERVICE_NAME}_mlb-bot --tail 50
    exit 1
fi
