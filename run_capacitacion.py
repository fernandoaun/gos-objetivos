"""
Iniciar GOS Capacitación (programa separado, Option B).
Puerto default: 5002 — base: instance/capacitacion/gos_cap.db
"""
import os
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

os.environ["GOS_APP_MODE"] = "capacitacion"
os.environ.setdefault("GOS_PORT", "5002")
cap_db = ROOT / "instance" / "capacitacion" / "gos_cap.db"
os.environ["GOS_DATABASE_PATH"] = os.environ.get("GOS_DATABASE_PATH") or str(cap_db)

from gos import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("GOS_PORT", "5002") or "5002")
    url = f"http://127.0.0.1:{port}/"
    print("=" * 52)
    print("  GOS — Capacitación (programa separado)")
    print("=" * 52)
    print(f"  Navegador: {url}")
    print(f"  Base: instance/capacitacion/gos_cap.db")
    print("  NO CIERRES esta ventana mientras uses el sistema")
    print("=" * 52)
    webbrowser.open(url)
    app.run(host="127.0.0.1", port=port, debug=True, use_reloader=False)
