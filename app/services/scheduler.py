"""
Scheduler para ejecutar jobs automáticos
- Job de 6 AM: Obtener resultados de ayer y calcular precisión
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .results_fetcher import results_fetcher
from .accuracy_calculator import accuracy_calculator
from ..models.database import get_db, get_prediction_by_game, update_prediction_result, save_prediction, save_game_result

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None


async def fetch_yesterday_results():
    """
    Job que se ejecuta a las 6 AM diariamente
    1. Obtiene los resultados de los partidos de ayer
    2. Compara con las predicciones guardadas
    3. Actualiza la base de datos con los resultados
    4. Calcula métricas de precisión
    """
    logger.info("=" * 50)
    logger.info("INICIANDO JOB: Fetch Yesterday Results")
    logger.info(f"Fecha de ejecución: {datetime.now()}")
    logger.info("=" * 50)
    
    yesterday = date.today() - timedelta(days=1)
    logger.info(f"Buscando resultados para: {yesterday}")
    
    try:
        completed_games = await results_fetcher.get_completed_games(yesterday)
        
        if not completed_games:
            logger.warning(f"No se encontraron partidos completados para {yesterday}")
            return
        
        logger.info(f"Encontrados {len(completed_games)} partidos completados")
        
        comparisons = []
        updated_count = 0
        
        for game in completed_games:
            game_id = game.get("game_id")
            home_team = game.get("home_team")
            away_team = game.get("away_team")
            
            logger.info(f"Procesando: {away_team} @ {home_team} - {game.get('home_score')}-{game.get('away_score')}")
            
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                prediction = get_prediction_by_game(db, game_id)
                
                if prediction:
                    comparison = accuracy_calculator.compare_prediction_with_result(
                        {
                            "predicted_home_score": prediction.predicted_home_score,
                            "predicted_away_score": prediction.predicted_away_score,
                            "predicted_total": prediction.predicted_total,
                            "predicted_favorite": prediction.predicted_favorite,
                            "over_line": prediction.over_line,
                            "over_probability": prediction.over_probability,
                            "home_team": prediction.home_team,
                            "away_team": prediction.away_team,
                        },
                        game
                    )
                    
                    update_prediction_result(
                        db,
                        game_id,
                        game.get("home_score", 0),
                        game.get("away_score", 0)
                    )
                    
                    # Also save to game_results table for dashboard
                    ou_prediction = "OVER" if prediction.over_probability > 0.5 else "UNDER"
                    actual_total = game.get("home_score", 0) + game.get("away_score", 0)
                    ou_actual = "OVER" if actual_total > prediction.over_line else "UNDER"
                    
                    result_data = {
                        "game_id": game_id,
                        "game_date": yesterday,
                        "home_team": home_team,
                        "away_team": away_team,
                        "predicted_home_score": prediction.predicted_home_score,
                        "predicted_away_score": prediction.predicted_away_score,
                        "predicted_total": prediction.predicted_total,
                        "predicted_favorite": prediction.predicted_favorite,
                        "over_line": prediction.over_line,
                        "over_probability": prediction.over_probability,
                        "actual_home_score": game.get("home_score", 0),
                        "actual_away_score": game.get("away_score", 0),
                        "actual_total": actual_total,
                        "actual_winner": game.get("winner"),
                        "ml_correct": comparison.get("ml_correct", False),
                        "ou_correct": comparison.get("ou_correct", False),
                        "rl_correct": comparison.get("rl_correct", False),
                        "score_error": comparison.get("score_error", 0),
                        "total_error": comparison.get("total_error", 0),
                        "ml_prediction": prediction.predicted_favorite,
                        "ml_actual": game.get("winner"),
                        "ou_prediction": ou_prediction,
                        "ou_actual": ou_actual
                    }
                    
                    try:
                        save_game_result(db, result_data)
                        logger.info(f"  Game result saved to dashboard table")
                    except Exception as e:
                        logger.error(f"  Error saving game result: {e}")
                    
                    comparisons.append(comparison)
                    updated_count += 1
                    
                    logger.info(
                        f"  ML: {'✓' if comparison['ml_correct'] else '✗'} | "
                        f"O/U: {'✓' if comparison['ou_correct'] else '✗'} | "
                        f"Score Error: {comparison['score_error']}"
                    )
                else:
                    logger.warning(f"No se encontró predicción para game_id {game_id}")
                    
            except Exception as e:
                logger.error(f"Error procesando game_id {game_id}: {e}")
            finally:
                db.close()
        
        if comparisons:
            metrics = accuracy_calculator.calculate_accuracy_metrics(comparisons)
            
            logger.info("=" * 50)
            logger.info("RESULTADOS DEL DÍA")
            logger.info(f"Partidos procesados: {len(comparisons)}")
            logger.info(f"ML Accuracy: {metrics['ml_accuracy']}% ({metrics['ml_correct']}/{metrics['total_games']})")
            logger.info(f"O/U Accuracy: {metrics['ou_accuracy']}% ({metrics['ou_correct']}/{metrics['total_games']})")
            logger.info(f"RL Accuracy: {metrics['rl_accuracy']}% ({metrics['rl_correct']}/{metrics['total_games']})")
            logger.info(f"Avg Score Error: {metrics['avg_score_error']} carreras")
            logger.info(f"Avg Total Error: {metrics['avg_total_error']} carreras")
            logger.info("=" * 50)
        
        logger.info(f"Job completado. {updated_count} predicciones actualizadas.")
        
    except Exception as e:
        logger.error(f"Error en job fetch_yesterday_results: {e}", exc_info=True)


async def fetch_last_7_days():
    """
    Job semanal: Obtiene resultados de los últimos 7 días
    Útil para sincronizar datos faltantes
    """
    logger.info("=" * 50)
    logger.info("INICIANDO JOB: Fetch Last 7 Days Results")
    logger.info("=" * 50)
    
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=7)
    
    try:
        all_games = await results_fetcher.get_all_completed_games_since(start_date, end_date)
        
        logger.info(f"Encontrados {len(all_games)} partidos en los últimos 7 días")
        
        updated = 0
        for game in all_games:
            try:
                db_gen = get_db()
                db = next(db_gen)
                
                game_id = game.get("game_id")
                prediction = get_prediction_by_game(db, game_id)
                
                if prediction and not prediction.result_registered:
                    update_prediction_result(
                        db,
                        game_id,
                        game.get("home_score", 0),
                        game.get("away_score", 0)
                    )
                    updated += 1
                
                db.close()
            except Exception as e:
                logger.error(f"Error actualizando {game.get('game_id')}: {e}")
        
        logger.info(f"Job completado. {updated} predicciones actualizadas.")
        
    except Exception as e:
        logger.error(f"Error en job fetch_last_7_days: {e}", exc_info=True)


def start_scheduler():
    """Inicia el scheduler con los jobs configurados"""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler ya está corriendo")
        return scheduler
    
    scheduler = AsyncIOScheduler()
    
    scheduler.add_job(
        fetch_yesterday_results,
        CronTrigger(hour=6, minute=0),
        id="fetch_yesterday_results",
        name="Fetch Yesterday Results (6 AM)",
        replace_existing=True
    )
    
    scheduler.add_job(
        fetch_last_7_days,
        CronTrigger(day_of_week="mon", hour=7, minute=0),
        id="fetch_last_7_days",
        name="Fetch Last 7 Days (Monday 7 AM)",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler iniciado correctamente")
    logger.info("Jobs programados:")
    logger.info("  - fetch_yesterday_results: Diariamente a las 6:00 AM")
    logger.info("  - fetch_last_7_days: Lunes a las 7:00 AM")
    
    return scheduler


def stop_scheduler():
    """Detiene el scheduler"""
    global scheduler
    
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler detenido")


def get_scheduler_status() -> dict:
    """Retorna el estado del scheduler"""
    global scheduler
    
    if scheduler is None:
        return {"running": False, "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None
        })
    
    return {
        "running": True,
        "jobs": jobs
    }


async def run_now():
    """Ejecuta el job de resultados inmediatamente (para testing)"""
    logger.info("Ejecutando job manualmente...")
    await fetch_yesterday_results()
