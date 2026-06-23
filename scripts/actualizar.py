"""Actualiza base de datos, logo y dependencias. Uso: python scripts\\actualizar.py"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    print("Actualizando GOS Objetivos...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"])
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "init_db.py")])
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "seed_demo.py")])
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "copiar_logo.py")])
    subprocess.run([sys.executable, str(ROOT / "scripts" / "crear_icono.py")], check=False)
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "renumerar_foda.py")])
    from app.version import APP_VERSION_LABEL

    print(f"Listo — {APP_VERSION_LABEL}")
    print("Cerra la ventana 'GOS - Servidor' si estaba abierta y usa ABRIR GOS Objetivos.bat")


if __name__ == "__main__":
    main()
