"""Copia el logo GOS al proyecto si falta. Uso: python scripts\\copiar_logo.py"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "static" / "img" / "gos-logo.png"

SOURCES = [
    ROOT / "static" / "img" / "gos-logo.png",
    Path(r"C:\Users\ferna\.cursor\projects\c-Users-ferna-OneDrive-GOS-GOS-Objetivos\assets")
    / "c__Users_ferna_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_image-89db5d65-b96a-4e29-8953-02d2c00e004b.png",
]


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.is_file() and DEST.stat().st_size > 1000:
        print(f"Logo OK: {DEST} ({DEST.stat().st_size} bytes)")
        return 0

    for src in SOURCES[1:]:
        if src.is_file():
            shutil.copy2(src, DEST)
            print(f"Logo copiado a {DEST}")
            return 0

    print("ERROR: No se encontró el archivo del logo.")
    print("Colocá manualmente la imagen en:")
    print(f"  {DEST}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
