# MLB Betting Bot

Bot de apuestas MLB con sabermetría avanzada que consulta la API oficial de MLB y genera predicciones de Money Line y Over/Under.

## Características

- Consulta partidos del día desde la API oficial de MLB (statsapi.mlb.com)
- Predicciones usando métricas sabermétricas:
  - ERA y FIP de pitchers abridores
  - Estadísticas de lineup (wOBA, OPS, K%)
  - Bullpen stats
  - Rendimiento reciente (últimos 15 juegos)
  - Factor de parque
- Integración con The Odds API (lineas de casino)
- Promedio de 4 bookmakers (DraftKings, FanDuel, BetMGM, LowVig)
- Alertas de movimiento de líneas
- Registro de resultados y tracking de precisión
- Base de datos PostgreSQL para persistencia

## Uso Local (Desarrollo)

```bash
pip install -r requirements.txt
python run.py
# o
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Deploy en Servidor (Docker Swarm)

### Requisitos
- Ubuntu/Debian Server
- Docker instalado
- Puerto 8000 abierto

### Instalación

```bash
# Conectar por SSH
ssh root@209.126.125.32

# Clonar repositorio
cd /opt
git clone https://github.com/xxsotoxx/mlb-bot.git
cd mlb-bot

# Hacer scripts ejecutables
chmod +x deploy.sh update.sh status.sh

# Deploy inicial
./deploy.sh
```

### Comandos Utiles

```bash
# Ver estado
./status.sh

# Ver logs en tiempo real
docker service logs mlb-bot_mlb-bot -f

# Actualizar despues de push a GitHub
./update.sh

# Reiniciar
docker stack rm mlb-bot
./deploy.sh
```

## Endpoints

| Endpoint | Descripcion |
|----------|-------------|
| `http://209.126.125.32:8000/` | Pagina principal |
| `http://209.126.125.32:8000/api/games/today` | Predicciones del dia |
| `http://209.126.125.32:8000/docs` | Documentacion Swagger |

## Estructura del Proyecto

```
mlb-bot/
├── app/
│   ├── main.py           # Aplicacion FastAPI
│   ├── routes/           # Endpoints
│   │   ├── games.py     # Partidos y predicciones
│   │   └── stats.py     # Estadisticas
│   ├── services/         # Logica de negocio
│   │   ├── mlb_api.py  # Cliente API MLB
│   │   ├── advanced_predictor.py  # Motor sabermetrico
│   │   ├── odds_api.py  # The Odds API
│   │   └── stats_service.py
│   ├── models/          # Modelos de datos
│   └── templates/       # Templates HTML
├── docker-compose.yml   # Config Docker Swarm
├── Dockerfile          # Imagen Docker
├── deploy.sh          # Script deploy
├── update.sh          # Script actualizacion
├── status.sh          # Script estado
└── requirements.txt   # Dependencias
```

## Docker Swarm

### Servicios
- **mlb-bot**: API FastAPI (puerto 8000)
- **postgres**: Base de datos PostgreSQL (puerto 5432 interno)

### Persistencia
- PostgreSQL guarda datos en volumen Docker
- Lineas historicas para alertas
- Estadisticas de predicciones

## API MLB

- Endpoint: `https://statsapi.mlb.com/api`
- No requiere autenticacion

## The Odds API

- Endpoint: `https://api.the-odds-api.com`
- 4 bookmakers: DraftKings, FanDuel, BetMGM, LowVig
- Promedio de lineas para mayor precision

## Notas

- Puerto 8000 debe estar abierto en firewall
- PostgreSQL solo accesible desde dentro de Docker
- Datos persisten en volumen Docker
