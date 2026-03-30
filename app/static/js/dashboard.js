let selectedGameId = null;

async function loadDashboard() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        
        if (data.success) {
            updateStats(data.data);
            loadHistory();
        }
    } catch (error) {
        console.error('Error cargando dashboard:', error);
    }
}

function updateStats(stats) {
    document.getElementById('total-predictions').textContent = stats.total_predictions || 0;
    document.getElementById('money-line-pct').textContent = (stats.money_line_percentage || 0) + '%';
    document.getElementById('ou-pct').textContent = (stats.over_under_percentage || 0) + '%';
    document.getElementById('avg-diff').textContent = (stats.avg_run_difference || 0).toFixed(1);
}

async function loadHistory() {
    try {
        const response = await fetch('/api/predictions/history?limit=100');
        const data = await response.json();
        
        if (data.success && data.data && data.data.predictions) {
            renderHistory(data.data.predictions);
        }
    } catch (error) {
        console.error('Error cargando historial:', error);
    }
}

function renderHistory(predictions) {
    const tbody = document.getElementById('history-table-body');
    
    if (!predictions || predictions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No hay predicciones en el historial</td></tr>';
        return;
    }
    
    tbody.innerHTML = predictions.map(p => {
        const hasResult = p.result_registered && p.actual_home_score !== null;
        const prediction = `${p.predicted_home_score.toFixed(0)}-${p.predicted_away_score.toFixed(0)}`;
        const actual = hasResult ? `${p.actual_home_score}-${p.actual_away_score}` : 'N/A';
        const resultClass = hasResult ? (p.actual_home_score > p.actual_away_score ? 
            (p.predicted_favorite === p.home_team ? 'text-success' : 'text-danger') : 
            (p.predicted_favorite === p.away_team ? 'text-success' : 'text-danger')) : '';
        
        let formattedDate = 'N/A';
        if (p.game_date) {
            try {
                const d = new Date(p.game_date);
                formattedDate = d.toLocaleDateString('es-MX', { timeZone: 'America/Mexico_City', year: 'numeric', month: 'short', day: 'numeric' });
            } catch {
                formattedDate = p.game_date;
            }
        }
        
        return `
            <tr>
                <td>${formattedDate}</td>
                <td>${p.away_team} @ ${p.home_team}</td>
                <td>${prediction}</td>
                <td class="${resultClass}">${actual}</td>
                <td>${p.predicted_favorite}</td>
                <td>Ov ${p.over_line}</td>
                <td>
                    ${hasResult ? 
                        '<span class="badge bg-success">Completado</span>' : 
                        `<button class="btn btn-sm btn-outline-secondary" onclick="openResultModalDashboard(${p.game_id}, '${p.home_team}', '${p.away_team}')">
                            <i class="bi bi-clipboard-check"></i> Resultado
                        </button>`
                    }
                </td>
            </tr>
        `;
    }).join('');
}

function openResultModalDashboard(gameId, homeTeam, awayTeam) {
    selectedGameId = gameId;
    document.getElementById('modal-game-info').textContent = `${awayTeam} @ ${homeTeam}`;
    document.getElementById('modal-home-score').value = 0;
    document.getElementById('modal-away-score').value = 0;
    new bootstrap.Modal(document.getElementById('resultModal')).show();
}

async function registrarResultadoDashboard() {
    if (!selectedGameId) return;
    
    const homeScore = parseInt(document.getElementById('modal-home-score').value) || 0;
    const awayScore = parseInt(document.getElementById('modal-away-score').value) || 0;
    
    try {
        const response = await fetch(`/api/predictions/${selectedGameId}/result`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ home_score: homeScore, away_score: awayScore })
        });
        
        const data = await response.json();
        
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('resultModal')).hide();
            loadDashboard();
        } else {
            alert('Error: ' + (data.error || data.message));
        }
    } catch (error) {
        alert('Error al registrar resultado');
    }
}

document.addEventListener('DOMContentLoaded', loadDashboard);
