"""
Iniciar GOS Objetivos sin el módulo Capacitación (Option B).
Base default: instance/objetivos/gos.db si existe; si no, instance/gos.db.
"""
import os
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

os.environ["GOS_APP_MODE"] = "objetivos"
os.environ.setdefault("GOS_PORT", "5001")
os.environ.setdefault("GOS_CAPACITACION_URL", "http://127.0.0.1:5002/gos/capacitacion")

obj_db = ROOT / "instance" / "objetivos" / "gos.db"
if obj_db.is_file():
    os.environ["GOS_DATABASE_PATH"] = os.environ.get("GOS_DATABASE_PATH") or str(obj_db)

from wsgi import app

if __name__ == "__main__":
    port = int(os.environ.get("GOS_PORT", "5001") or "5001")
    url = f"http://127.0.0.1:{port}/"
    print("=" * 52)
    print("  GOS — Objetivos (sin Capacitación local)")
    print("=" * 52)
    print(f"  Navegador: {url}")
    print(f"  Modo: {os.environ.get('GOS_APP_MODE')}")
    print(f"  Cap externa: {os.environ.get('GOS_CAPACITACION_URL')}")
    print("  NO CIERRES esta ventana mientras uses el sistema")
    print("=" * 52)
    webbrowser.open(url)
    app.run(host="127.0.0.1", port=port, debug=True, use_reloader=False)
