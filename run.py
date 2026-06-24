"""
Iniciar GOS Objetivos.
Doble clic en: ABRIR GOS Objetivos.bat
"""
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gos.modulos.objetivos.version import APP_VERSION, APP_VERSION_LABEL
from wsgi import app

if __name__ == "__main__":
    logo = ROOT / "static" / "img" / "gos-logo.png"
    if not logo.is_file():
        try:
            import subprocess

            subprocess.run([sys.executable, str(ROOT / "scripts" / "copiar_logo.py")], check=False)
        except Exception:
            pass

    url = "http://127.0.0.1:5000/gos/objetivos/dashboard/"
    print("=" * 52)
    print("  GOS — Plataforma modular")
    print(f"  Modulo Objetivos — {APP_VERSION_LABEL}")
    print("=" * 52)
    print(f"  Navegador: {url}")
    print("  Entrada directa (sin login)")
    print()
    print("  FODA: menu lateral -> importar Word, editar, PDF")
    print("  NO CIERRES esta ventana mientras uses el sistema")
    print("=" * 52)

    webbrowser.open(url)
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
