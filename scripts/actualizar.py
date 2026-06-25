"""Actualiza base de datos, logo, .env y dependencias."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    env_file = ROOT / ".env"
    if not env_file.is_file():
        print("Creando .env inicial...")
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "setup_env.py")])

    print("Actualizando GOS...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"])
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "check_env.py")])
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "init_db.py")])
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "seed_demo.py")])
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "copiar_logo.py")])
    subprocess.run([sys.executable, str(ROOT / "scripts" / "crear_icono.py")], check=False)
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "renumerar_foda.py")])
    from gos.version import APP_VERSION_LABEL

    print(f"Listo — {APP_VERSION_LABEL}")
    print("Usá ABRIR GOS Objetivos.bat para iniciar.")


if __name__ == "__main__":
    main()
