"""Almacenamiento de certificados VTV."""

from __future__ import annotations

from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".webp")
MAX_BYTES = 10 * 1024 * 1024


def certificados_dir() -> Path:
    base = Path(current_app.root_path).parent / "storage" / "mantenimiento" / "vtv"
    base.mkdir(parents=True, exist_ok=True)
    return base


def validar_certificado(file_storage) -> str:
    if not file_storage or not file_storage.filename:
        raise ValueError("Debe enviar un archivo de certificado.")
    filename = secure_filename(file_storage.filename)
    if not filename:
        raise ValueError("Nombre de archivo inválido.")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("Solo se admiten PDF o imágenes (JPG, PNG, WebP).")
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_BYTES:
        raise ValueError("El certificado no puede superar 10 MB.")
    return filename


def guardar_certificado(turno_id: int, file_storage) -> tuple[str, str]:
    """Guarda el archivo y devuelve (ruta_absoluta, nombre_original_seguro)."""
    filename = validar_certificado(file_storage)
    ext = Path(filename).suffix.lower()
    dest = certificados_dir() / f"turno_{turno_id}{ext}"
    if dest.is_file():
        dest.unlink(missing_ok=True)
    file_storage.save(dest)
    return str(dest), filename


def borrar_certificado(path_str: str | None) -> None:
    if not path_str:
        return
    path = Path(path_str)
    if path.is_file():
        path.unlink(missing_ok=True)
