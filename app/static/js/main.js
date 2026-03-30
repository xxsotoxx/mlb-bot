let selectedGameId = null;

function formatDate() {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('current-date').textContent = new Date().toLocaleDateString('es-ES', options);
}

function formatGameTime(dateStr) {
    if (!dateStr) return 'TBD';
    try {
        const d = new Date(dateStr);
        return d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Mexico_City' });
    } catch {
        return dateStr;
    }
}

async function consultarPartidos() {
    const btn = document.getElementById('btn-consultar');
    const spinner = document.getElementById('loading-spinner');
    const container = document.getElementById('games-container');
    
    btn.disabled = true;
    spinner.style.display = 'block';
    container.innerHTML = '<div class="col-12 text-center"><p class="text-muted">Consultando API de MLB...</p></div>';
    
    try {
        const response = await fetch('/api/games/today');
        const data = await response.json();
        
        if (data.success && data.data && data.data.games && data.data.games.length > 0) {
            renderGames(data.data.games);
        } else {
            container.innerHTML = `
                <div class="col-12 text-center">
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle"></i> ${data.message || 'No hay partidos programados para hoy'}
                    </div>
                </div>
            `;
        }
    } catch (error) {
        container.innerHTML = `
            <div class="col-12 text-center">
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Error al conectar con la API de MLB
                </div>
            </div>
        `;
    } finally {
        btn.disabled = false;
        spinner.style.display = 'none';
    }
}

function renderGames(games) {
    const container = document.getElementById('games-container');
    container.innerHTML = '';
    
    games.forEach(game => {
        const card = document.createElement('div');
        card.className = 'col-12';
        card.innerHTML = createGameCard(game);
        container.appendChild(card);
    });
}

function getConfidenceBadgeClass(level) {
    switch (level?.toLowerCase()) {
        case 'high': return 'badge-high';
        case 'medium': return 'badge-medium';
        default: return 'badge-low';
    }
}

function createGameCard(game) {
    const awayTeam = game.away_team || 'Visitante';
    const homeTeam = game.home_team || 'Local';
    const awayScore = Math.round(game.predicted_away_score || 0);
    const homeScore = Math.round(game.predicted_home_score || 0);
    const predictedTotal = game.predicted_total || 0;
    
    const confidenceClass = getConfidenceBadgeClass(game.confidence_level);
    const confidenceText = game.confidence_spanish || 'BAJA';
    const confidencePct = game.confidence_percentage || 50;
    const confidenceDesc = game.confidence_description || '';
    
    const casinoComparison = game.casino_comparison || {};
    const casinoLine = game.casino_line || {};
    const casinoSource = game.casino_source || 'Estimado';
    const favorite = game.predicted_favorite || homeTeam;
    
    const homeProb = game.home_win_probability || 50;
    const awayProb = game.away_win_probability || 50;
    const overProb = game.over_probability || 50;
    const underProb = game.under_probability || 50;
    
    const homePitcher = game.pitcher_home || 'TBD';
    const awayPitcher = game.pitcher_away || 'TBD';
    const homePitcherEra = game.home_pitcher_stats?.era?.toFixed(2) || 'N/A';
    const awayPitcherEra = game.away_pitcher_stats?.era?.toFixed(2) || 'N/A';
    const homeBullpenEra = game.home_bullpen_stats?.era?.toFixed(2) || 'N/A';
    const awayBullpenEra = game.away_bullpen_stats?.era?.toFixed(2) || 'N/A';
    
    const mlData = casinoComparison.money_line || {};
    const ouData = casinoComparison.over_under || {};
    const spreadData = casinoComparison.run_line || {};
    
    const casinoOULine = ouData.casino_line || game.over_line || 8;
    const ouDiff = predictedTotal - casinoOULine;
    const isOver = ouDiff > 0;
    const ouRecommendation = isOver 
        ? `+${ouDiff.toFixed(1)} OVER` 
        : `${Math.abs(ouDiff).toFixed(1)} UNDER`;
    const ouValue = ouData.value || 'BAJO';
    const ouConfidence = ouData.confidence || 50;
    
    const mlFavorite = mlData.favorite || favorite;
    const mlFavoriteMargin = mlData.favorite_margin || 0;
    const mlConfidence = mlData.confidence || 'BAJA';
    const mlMatch = mlData.prediction_match !== false;
    
    const recommendedBookmaker = casinoLine.recommended_bookmaker || 'Promedio de 4 bookmakers';
    
    const consensusLine = casinoLine.consensus_line || 8;
    const consensusCount = casinoLine.consensus_bookmaker_count || 4;
    const consensusTotal = casinoLine.consensus_total_bookmakers || 4;
    
    return `
        <div class="card game-card mb-4">
                <div class="card-header d-flex justify-content-between align-items-center" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white;">
                <div>
                    <strong>${game.venue || 'Estadio desconocido'}</strong>
                    <span class="ms-2" style="color: #ffffff;">${formatGameTime(game.game_date) || 'TBD'}</span>
                    <span class="badge bg-primary ms-2" style="font-size: 0.6rem;">
                        ${recommendedBookmaker}
                    </span>
                    <span class="badge bg-info ms-1" style="font-size: 0.55rem;">
                        Consenso: ${consensusLine} (${consensusCount}/${consensusTotal})
                    </span>
                </div>
                <div class="text-end">
                    <span class="badge ${confidenceClass}">
                        CONFIANZA ${confidenceText} (${confidencePct}%)
                    </span>
                    ${confidenceDesc ? `<div style="font-size: 0.65rem; color: #d1d5da; margin-top: 2px;">${confidenceDesc}</div>` : ''}
                </div>
            </div>
            <div class="card-body p-0">
                <div class="prediction-main">
                    <div class="prediction-score">
                        <div class="team-away text-end">
                            <h3 class="mb-1" style="color: #ffffff;">${awayTeam}</h3>
                            <small style="color: #d1d5da;">${awayPitcher}</small>
                            <div class="pitcher-stats mt-1">
                                <span class="badge" style="background-color: #4a5568;">ERA: ${awayPitcherEra}</span>
                                <span class="badge" style="background-color: #2d3748;">Bullpen: ${awayBullpenEra}</span>
                            </div>
                            ${mlData.home_odds ? `<div class="mt-1"><small style="color: #d1d5da;">ML: ${mlData.home_odds > 0 ? '+' : ''}${mlData.home_odds}</small></div>` : ''}
                        </div>
                        <div class="score-display">
                            <div class="final-score">
                                <span class="score-num">${awayScore}</span>
                                <span class="score-sep">-</span>
                                <span class="score-num">${homeScore}</span>
                            </div>
                            <small style="color: #ffffff;">Total: ${predictedTotal.toFixed(1)} carreras</small>
                        </div>
                        <div class="team-home text-start">
                            <h3 class="mb-1" style="color: #ffffff;">${homeTeam}</h3>
                            <small style="color: #d1d5da;">${homePitcher}</small>
                            <div class="pitcher-stats mt-1">
                                <span class="badge" style="background-color: #4a5568;">ERA: ${homePitcherEra}</span>
                                <span class="badge" style="background-color: #2d3748;">Bullpen: ${homeBullpenEra}</span>
                            </div>
                            ${mlData.away_odds ? `<div class="mt-1"><small style="color: #d1d5da;">ML: ${mlData.away_odds > 0 ? '+' : ''}${mlData.away_odds}</small></div>` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="prediction-details">
                    <div class="row g-0">
                        <div class="col-md-4 border-end">
                            <div class="p-3 text-center">
                                <h6 class="text-primary mb-2">GANADOR (MONEY LINE)</h6>
                                <h5 class="text-success mb-1">${favorite}</h5>
                                <div class="mb-2">
                                    <small style="color: ${mlMatch ? '#3fb950' : '#f85149'};">
                                        ${mlMatch ? '✓' : '✗'} Casino: ${mlFavorite}
                                    </small>
                                </div>
                                <div class="prob-bar">
                                    <div class="prob-track">
                                        <div class="prob-fill-away" style="width: ${awayProb}%"></div>
                                        <div class="prob-fill-home" style="width: ${homeProb}%"></div>
                                    </div>
                                    <div class="prob-labels" style="color: #ffffff;">
                                        <span style="color: #f85149;">${awayTeam}: ${awayProb}%</span>
                                        <span style="color: #3fb950;">${homeTeam}: ${homeProb}%</span>
                                    </div>
                                </div>
                                <div class="mt-2">
                                    <small style="color: #d1d5da;">Confianza ML: </small>
                                    <span class="badge ${mlConfidence === 'ALTA' || mlConfidence === 'MUY ALTA' ? 'bg-success' : mlConfidence === 'MEDIA' ? 'bg-warning' : 'bg-secondary'}">${mlConfidence}</span>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4 border-end">
                            <div class="p-3 text-center">
                                <h6 class="text-warning mb-2">OVER / UNDER</h6>
                                <div class="ou-comparison">
                                    <div class="ou-casino">
                                        <small style="color: #d1d5da;">Línea DraftKings</small>
                                        <h4 class="mb-0" style="color: #ffffff;">${casinoOULine}</h4>
                                        ${ouData.over_odds ? `<small style="color: #d1d5da;">Over: ${ouData.over_odds > 0 ? '+' : ''}${ouData.over_odds} | Under: ${ouData.under_odds > 0 ? '+' : ''}${ouData.under_odds}</small>` : ''}
                                    </div>
                                    <div class="ou-vs">VS</div>
                                    <div class="ou-prediction">
                                        <small style="color: #d1d5da;">Nuestro Pronóstico</small>
                                        <h4 class="mb-0 text-success">${predictedTotal.toFixed(1)}</h4>
                                    </div>
                                </div>
                                <div class="ou-recommendation mt-2">
                                    <span class="badge ${isOver ? 'bg-success' : 'bg-danger'}">
                                        ${ouRecommendation} (${ouData.edge || '0'})
                                    </span>
                                    <span class="badge ${ouValue === 'ALTO' || ouValue === 'MUY ALTO' ? 'bg-warning' : 'bg-secondary'} ms-1">
                                        VALOR ${ouValue}
                                    </span>
                                </div>
                                <div class="ou-probs mt-2" style="color: #ffffff;">
                                    <span style="color: ${isOver ? '#3fb950' : '#d1d5da'};">OVER ${ouConfidence}%</span>
                                    <span class="mx-2">|</span>
                                    <span style="color: ${!isOver ? '#f85149' : '#d1d5da'};">UNDER ${100 - ouConfidence}%</span>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-3 text-center">
                                <h6 class="text-info mb-2">RUN LINE</h6>
                                ${spreadData.casino_line ? `
                                    <h5 class="text-primary mb-1">${spreadData.recommendation || spreadData.casino_line}</h5>
                                    <div class="mb-2">
                                        <small style="color: #d1d5da;">
                                            Odds: Home ${spreadData.home_odds > 0 ? '+' : ''}${spreadData.home_odds || 'N/A'} | Away ${spreadData.away_odds > 0 ? '+' : ''}${spreadData.away_odds || 'N/A'}
                                        </small>
                                    </div>
                                ` : '<small style="color: #d1d5da;">Run line no disponible</small>'}
                                <div class="stats-grid mt-2">
                                    <div class="stat-item">
                                        <small>Registro Local</small>
                                        <strong style="color: #ffffff;">${game.home_team_stats?.wins || 0}-${game.home_team_stats?.losses || 0}</strong>
                                    </div>
                                    <div class="stat-item">
                                        <small>Registro Visitante</small>
                                        <strong style="color: #ffffff;">${game.away_team_stats?.wins || 0}-${game.away_team_stats?.losses || 0}</strong>
                                    </div>
                                    <div class="stat-item">
                                        <small>Factor Parque</small>
                                        <strong style="color: #ffffff;">${(game.park_factor || 1).toFixed(2)}</strong>
                                    </div>
                                </div>
                                ${!casinoLine.available ? '<small class="d-block mt-2" style="color: #d29922;">* Línea no disponible - usando estimación</small>' : ''}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function openResultModal(gameId, homeTeam, awayTeam) {
    selectedGameId = gameId;
    document.getElementById('modal-game-info').textContent = `${awayTeam} @ ${homeTeam}`;
    document.getElementById('home-score').value = 0;
    document.getElementById('away-score').value = 0;
    new bootstrap.Modal(document.getElementById('resultModal')).show();
}

async function registrarResultado() {
    if (!selectedGameId) return;
    
    const homeScore = parseInt(document.getElementById('home-score').value) || 0;
    const awayScore = parseInt(document.getElementById('away-score').value) || 0;
    
    try {
        const response = await fetch(`/api/predictions/${selectedGameId}/result`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ home_score: homeScore, away_score: awayScore })
        });
        
        const data = await response.json();
        
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('resultModal')).hide();
            alert('Resultado registrado exitosamente');
            consultarPartidos();
        } else {
            alert('Error: ' + (data.error || data.message));
        }
    } catch (error) {
        alert('Error al registrar resultado');
    }
}

document.addEventListener('DOMContentLoaded', formatDate);
