"""Genera gos-logo.ico para el acceso directo del Escritorio. Uso: python scripts\\crear_icono.py"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PNG = ROOT / "static" / "img" / "gos-logo.png"
ICO = ROOT / "static" / "img" / "gos-logo.ico"


def main() -> int:
    if not PNG.is_file():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "copiar_logo.py")], check=False)
    if not PNG.is_file():
        print("ERROR: Falta static/img/gos-logo.png")
        return 1

    png = str(PNG).replace("'", "''")
    ico = str(ICO).replace("'", "''")
    ps = f"""
Add-Type -AssemblyName System.Drawing
$bmp = [System.Drawing.Bitmap]::FromFile('{png}')
$icon = [System.Drawing.Icon]::FromHandle($bmp.GetHicon())
$fs = [System.IO.FileStream]::new('{ico}', [System.IO.FileMode]::Create)
$icon.Save($fs)
$fs.Close()
$bmp.Dispose()
"""
    ICO.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not ICO.is_file():
        print("ERROR al crear .ico:", r.stderr or r.stdout)
        return 1
    print(f"Icono OK: {ICO} ({ICO.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
