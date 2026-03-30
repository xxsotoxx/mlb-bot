#!/bin/bash

echo "=============================================="
echo "  MLB Bot - Status Script"
echo "=============================================="
echo ""

PROJECT_NAME="mlb-bot"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Estado de servicios
echo "Estado de Servicios Docker Swarm:"
echo "-----------------------------------"
docker service ls | grep $PROJECT_NAME

echo ""
echo "Detalles de Servicios:"
echo "-----------------------------------"

if docker service ls | grep -q ${PROJECT_NAME}_mlb-bot; then
    echo -e "${GREEN}[MLB Bot]${NC} - Running"
    docker service ps ${PROJECT_NAME}_mlb-bot
else
    echo -e "${RED}[MLB Bot]${NC} - Not Running"
fi

echo ""

if docker service ls | grep -q ${PROJECT_NAME}_postgres; then
    echo -e "${GREEN}[PostgreSQL]${NC} - Running"
    docker service ps ${PROJECT_NAME}_postgres
else
    echo -e "${RED}[PostgreSQL]${NC} - Not Running"
fi

echo ""
echo "Logs Recientes (MLB Bot):"
echo "-----------------------------------"
docker service logs ${PROJECT_NAME}_mlb-bot --tail 10

echo ""
echo "Puertos Expuestos:"
echo "-----------------------------------"
docker ps --filter "name=${PROJECT_NAME}" --format "table {{.Names}}\t{{.Ports}}"

echo ""
echo "Uso de Recursos:"
echo "-----------------------------------"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
