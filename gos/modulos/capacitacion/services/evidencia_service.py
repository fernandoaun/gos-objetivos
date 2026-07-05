from __future__ import annotations

from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    CertificacionEmpleado,
    EncuentroCapacitacion,
    Participante,
    RegistroCapacitacion,
)

ALLOWED_EXT = (".pdf",)
ALLOWED_FOTO_EXT = (".jpg", ".jpeg", ".png", ".webp")
MAX_BYTES = 10 * 1024 * 1024
MAX_FOTO_BYTES = 5 * 1024 * 1024


def _upload_dir(empresa_id: int, sub: str) -> Path:
    base = Path(current_app.root_path).parent / "storage" / "capacitacion" / str(empresa_id) / sub
    base.mkdir(parents=True, exist_ok=True)
    return base


def _validar_pdf(file_storage) -> str:
    if not file_storage or not file_storage.filename:
        raise ValueError("Debe enviar un archivo PDF.")
    filename = secure_filename(file_storage.filename)
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Solo se admiten archivos PDF.")
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_BYTES:
        raise ValueError("El archivo no puede superar 10 MB.")
    return filename


def _validar_imagen(file_storage) -> str:
    if not file_storage or not file_storage.filename:
        raise ValueError("Debe enviar una imagen.")
    filename = secure_filename(file_storage.filename)
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_FOTO_EXT:
        raise ValueError("Solo se admiten imágenes JPG, PNG o WebP.")
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_FOTO_BYTES:
        raise ValueError("La imagen no puede superar 5 MB.")
    return filename


def subir_foto_participante(empresa_id: int, participante_id: int, file_storage) -> dict:
    participante = Participante.query.filter_by(
        id=participante_id, empresa_id=empresa_id, activo=True
    ).first()
    if not participante:
        raise ValueError("Participante no encontrado")
    filename = _validar_imagen(file_storage)
    ext = Path(filename).suffix.lower()
    dest_dir = _upload_dir(empresa_id, "fotos")
    dest = dest_dir / f"part_{participante_id}{ext}"
    file_storage.save(dest)
    if participante.foto_path:
        old = Path(participante.foto_path)
        if old.is_file() and old != dest:
            old.unlink(missing_ok=True)
    participante.foto_path = str(dest)
    db.session.commit()
    return _participante_foto_dict(participante)


def descargar_foto_participante(empresa_id: int, participante_id: int) -> tuple[Path, str]:
    participante = Participante.query.filter_by(
        id=participante_id, empresa_id=empresa_id, activo=True
    ).first()
    if not participante or not participante.foto_path:
        raise ValueError("Foto no encontrada")
    path = Path(participante.foto_path)
    if not path.is_file():
        raise ValueError("Archivo no disponible")
    mimetype_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return path, mimetype_map.get(path.suffix.lower(), "image/jpeg")


def eliminar_foto_participante(empresa_id: int, participante_id: int) -> dict:
    participante = Participante.query.filter_by(
        id=participante_id, empresa_id=empresa_id, activo=True
    ).first()
    if not participante:
        raise ValueError("Participante no encontrado")
    if participante.foto_path:
        path = Path(participante.foto_path)
        if path.is_file():
            path.unlink(missing_ok=True)
        participante.foto_path = None
        db.session.commit()
    return _participante_foto_dict(participante)


def _participante_foto_dict(participante: Participante) -> dict:
    return {
        "id": participante.id,
        "foto_path": participante.foto_path,
        "tiene_foto": bool(participante.foto_path),
    }


def subir_certificado_registro(empresa_id: int, registro_id: int, file_storage) -> dict:
    reg = RegistroCapacitacion.query.filter_by(id=registro_id, empresa_id=empresa_id).first()
    if not reg:
        raise ValueError("Registro no encontrado")
    filename = _validar_pdf(file_storage)
    dest_dir = _upload_dir(empresa_id, "certificados")
    dest = dest_dir / f"reg_{registro_id}_{filename}"
    file_storage.save(dest)
    if reg.certificado_path:
        old = Path(reg.certificado_path)
        if old.is_file():
            old.unlink(missing_ok=True)
    reg.certificado_path = str(dest)
    db.session.commit()
    return _registro_evidencia_dict(reg)


def descargar_certificado_registro(empresa_id: int, registro_id: int) -> tuple[Path, str]:
    reg = RegistroCapacitacion.query.filter_by(id=registro_id, empresa_id=empresa_id).first()
    if not reg or not reg.certificado_path:
        raise ValueError("Certificado no encontrado")
    path = Path(reg.certificado_path)
    if not path.is_file():
        raise ValueError("Archivo no disponible")
    return path, path.name


def eliminar_certificado_registro(empresa_id: int, registro_id: int) -> dict:
    reg = RegistroCapacitacion.query.filter_by(id=registro_id, empresa_id=empresa_id).first()
    if not reg:
        raise ValueError("Registro no encontrado")
    if reg.certificado_path:
        path = Path(reg.certificado_path)
        if path.is_file():
            path.unlink(missing_ok=True)
        reg.certificado_path = None
        db.session.commit()
    return _registro_evidencia_dict(reg)


def subir_documento_certificacion(empresa_id: int, cert_id: int, file_storage) -> dict:
    cert = CertificacionEmpleado.query.filter_by(id=cert_id, empresa_id=empresa_id).first()
    if not cert:
        raise ValueError("Certificación no encontrada")
    filename = _validar_pdf(file_storage)
    dest_dir = _upload_dir(empresa_id, "certificaciones")
    dest = dest_dir / f"cert_{cert_id}_{filename}"
    file_storage.save(dest)
    if cert.documento_path:
        old = Path(cert.documento_path)
        if old.is_file():
            old.unlink(missing_ok=True)
    cert.documento_path = str(dest)
    db.session.commit()
    return {"id": cert.id, "documento_path": cert.documento_path, "tiene_documento": True}


def descargar_documento_certificacion(empresa_id: int, cert_id: int) -> tuple[Path, str]:
    cert = CertificacionEmpleado.query.filter_by(id=cert_id, empresa_id=empresa_id).first()
    if not cert or not cert.documento_path:
        raise ValueError("Documento no encontrado")
    path = Path(cert.documento_path)
    if not path.is_file():
        raise ValueError("Archivo no disponible")
    return path, path.name


def _registro_evidencia_dict(reg: RegistroCapacitacion) -> dict:
    return {
        "id": reg.id,
        "certificado_path": reg.certificado_path,
        "tiene_certificado": bool(reg.certificado_path),
    }


def subir_material_encuentro(empresa_id: int, encuentro_id: int, file_storage) -> dict:
    enc = EncuentroCapacitacion.query.filter_by(id=encuentro_id, empresa_id=empresa_id).first()
    if not enc:
        raise ValueError("Cronograma no encontrado")
    filename = _validar_pdf(file_storage)
    dest_dir = _upload_dir(empresa_id, "encuentros")
    dest = dest_dir / f"enc_{encuentro_id}_material_{filename}"
    file_storage.save(dest)
    enc.material_adjunto_url = str(dest)
    db.session.commit()
    return {"id": enc.id, "material_adjunto_url": enc.material_adjunto_url}


def subir_resultados_encuentro(empresa_id: int, encuentro_id: int, file_storage) -> dict:
    enc = EncuentroCapacitacion.query.filter_by(id=encuentro_id, empresa_id=empresa_id).first()
    if not enc:
        raise ValueError("Cronograma no encontrado")
    filename = _validar_pdf(file_storage)
    dest_dir = _upload_dir(empresa_id, "encuentros")
    dest = dest_dir / f"enc_{encuentro_id}_resultados_{filename}"
    file_storage.save(dest)
    enc.resultados_adjunto_url = str(dest)
    db.session.commit()
    return {"id": enc.id, "resultados_adjunto_url": enc.resultados_adjunto_url}
