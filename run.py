"""
MLB Betting Bot - Run Script
Ejecuta el servidor de desarrollo
"""
import uvicorn
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("=" * 50)
    print("  MLB Betting Bot - Inicializando...")
    print("=" * 50)
    print("  Accede a: http://localhost:8000")
    print("  Documentación: http://localhost:8000/docs")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
