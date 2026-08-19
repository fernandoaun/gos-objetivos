from __future__ import annotations

from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    CertificacionEmpleado,
    ClienteCapacitacion,
    EncuentroAdjunto,
    EncuentroCapacitacion,
    Participante,
    RegistroCapacitacion,
)
from gos.modulos.capacitacion.models.config import CapacitacionConfig

ALLOWED_EXT = (".pdf",)
ALLOWED_FOTO_EXT = (".jpg", ".jpeg", ".png", ".webp")
ALLOWED_EVIDENCIA_EXT = ALLOWED_EXT + ALLOWED_FOTO_EXT
MAX_BYTES = 10 * 1024 * 1024
MAX_FOTO_BYTES = 5 * 1024 * 1024


def _upload_dir(empresa_id: int, sub: str, *, crear: bool = True) -> Path:
    base = Path(current_app.root_path).parent / "storage" / "capacitacion" / str(empresa_id) / sub
    if crear:
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


def _validar_evidencia(file_storage) -> tuple[str, str]:
    if not file_storage or not file_storage.filename:
        raise ValueError("Debe enviar un archivo.")
    filename = secure_filename(file_storage.filename)
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EVIDENCIA_EXT:
        raise ValueError("Solo se admiten PDF o imágenes JPG, PNG o WebP.")
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    limite = MAX_BYTES if ext == ".pdf" else MAX_FOTO_BYTES
    if size > limite:
        raise ValueError("El archivo supera el tamaño máximo permitido.")
    mime = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")
    return filename, mime


def subir_adjunto_encuentro(empresa_id: int, encuentro_id: int, file_storage) -> dict:
    """Adjunta PDF o foto (asistencia / temas) a un encuentro; admite varios archivos."""
    enc = EncuentroCapacitacion.query.filter_by(id=encuentro_id, empresa_id=empresa_id).first()
    if not enc:
        raise ValueError("Cronograma no encontrado")
    filename, mime = _validar_evidencia(file_storage)
    dest_dir = _upload_dir(empresa_id, "encuentros")
    from uuid import uuid4

    dest = dest_dir / f"enc_{encuentro_id}_adj_{uuid4().hex[:10]}_{filename}"
    file_storage.save(dest)
    adj = EncuentroAdjunto(
        encuentro_id=encuentro_id,
        archivo_path=str(dest),
        nombre_original=filename,
        content_type=mime,
        tipo="evidencia",
    )
    db.session.add(adj)
    if not enc.material_adjunto_url:
        enc.material_adjunto_url = str(dest)
    db.session.commit()
    return {
        "id": adj.id,
        "encuentro_id": encuentro_id,
        "nombre_original": adj.nombre_original,
        "content_type": adj.content_type,
        "tipo": adj.tipo,
    }


def listar_adjuntos_encuentro(empresa_id: int, encuentro_id: int) -> list[dict]:
    enc = EncuentroCapacitacion.query.filter_by(id=encuentro_id, empresa_id=empresa_id).first()
    if not enc:
        raise ValueError("Cronograma no encontrado")
    return [
        {
            "id": a.id,
            "nombre_original": a.nombre_original,
            "content_type": a.content_type,
            "tipo": a.tipo,
        }
        for a in enc.adjuntos.all()
    ]


def descargar_adjunto_encuentro(empresa_id: int, encuentro_id: int, adjunto_id: int) -> tuple[Path, str]:
    enc = EncuentroCapacitacion.query.filter_by(id=encuentro_id, empresa_id=empresa_id).first()
    if not enc:
        raise ValueError("Cronograma no encontrado")
    adj = EncuentroAdjunto.query.filter_by(id=adjunto_id, encuentro_id=encuentro_id).first()
    if not adj or not adj.archivo_path:
        raise ValueError("Adjunto no encontrado")
    path = Path(adj.archivo_path)
    if not path.is_file():
        raise ValueError("Archivo no disponible")
    return path, adj.nombre_original or path.name


_MIME_IMG = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def _project_root() -> Path:
    return Path(current_app.root_path).parent


def _path_from_stored(stored: str | None) -> Path | None:
    if not stored:
        return None
    p = Path(stored)
    if p.is_file():
        return p
    rel = _project_root() / stored
    if rel.is_file():
        return rel
    return None


def _canonical_image(dest_dir: Path, stem: str) -> Path | None:
    if not dest_dir.is_dir():
        return None
    for ext in _MIME_IMG:
        cand = dest_dir / f"{stem}{ext}"
        if cand.is_file():
            return cand
    return None


def _store_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_project_root().resolve()))
    except ValueError:
        return str(path)


def _limpiar_otras_ext(dest: Path) -> None:
    for ext in _MIME_IMG:
        other = dest.with_suffix(ext)
        if other != dest and other.is_file():
            other.unlink(missing_ok=True)


def _resolver_logo(
    stored_path: str | None,
    blob: bytes | None,
    mime: str | None,
    dest_dir: Path,
    stem: str,
) -> tuple[Path | bytes, str]:
    path = _path_from_stored(stored_path) or _canonical_image(dest_dir, stem)
    if path:
        return path, _MIME_IMG.get(path.suffix.lower(), mime or "image/png")
    if blob:
        return blob, mime or "image/png"
    raise ValueError("Logo no encontrado")


def cliente_tiene_logo(cliente) -> bool:
    if getattr(cliente, "logo_bytes", None):
        return True
    dest_dir = _upload_dir(cliente.empresa_id, "logos", crear=False)
    return bool(_path_from_stored(cliente.logo_path) or _canonical_image(dest_dir, f"cli_{cliente.id}"))


def _guardar_imagen(dest: Path, file_storage) -> Path:
    filename = _validar_imagen(file_storage)
    ext = Path(filename).suffix.lower()
    dest = dest.with_suffix(ext)
    file_storage.save(dest)
    _limpiar_otras_ext(dest)
    return dest


def subir_logo_cliente(empresa_id: int, cliente_id: int, file_storage) -> dict:
    from gos.modulos.capacitacion.services.cliente_service import cliente_dict, obtener_cliente

    cliente = obtener_cliente(empresa_id, cliente_id)
    dest_dir = _upload_dir(empresa_id, "logos")
    dest = _guardar_imagen(dest_dir / f"cli_{cliente_id}", file_storage)
    if cliente.logo_path:
        old = _path_from_stored(cliente.logo_path)
        if old and old.is_file() and old != dest:
            old.unlink(missing_ok=True)
    cliente.logo_path = _store_rel(dest)
    cliente.logo_bytes = dest.read_bytes()
    cliente.logo_mime = _MIME_IMG.get(dest.suffix.lower(), "image/png")
    db.session.commit()
    return cliente_dict(cliente)


def descargar_logo_cliente(empresa_id: int, cliente_id: int) -> tuple[Path | bytes, str]:
    cliente = ClienteCapacitacion.query.filter_by(
        id=cliente_id, empresa_id=empresa_id, activo=True
    ).first()
    if not cliente:
        raise ValueError("Logo no encontrado")
    dest_dir = _upload_dir(empresa_id, "logos", crear=False)
    return _resolver_logo(
        cliente.logo_path,
        getattr(cliente, "logo_bytes", None),
        getattr(cliente, "logo_mime", None),
        dest_dir,
        f"cli_{cliente_id}",
    )


def eliminar_logo_cliente(empresa_id: int, cliente_id: int) -> dict:
    from gos.modulos.capacitacion.services.cliente_service import cliente_dict, obtener_cliente

    cliente = obtener_cliente(empresa_id, cliente_id)
    dest_dir = _upload_dir(empresa_id, "logos")
    found = _path_from_stored(cliente.logo_path) or _canonical_image(dest_dir, f"cli_{cliente_id}")
    if found and found.is_file():
        found.unlink(missing_ok=True)
    _limpiar_otras_ext(dest_dir / f"cli_{cliente_id}.png")
    cliente.logo_path = None
    cliente.logo_bytes = None
    cliente.logo_mime = None
    db.session.commit()
    return cliente_dict(cliente)


def subir_logo_empresa(empresa_id: int, file_storage) -> dict:
    from gos.modulos.capacitacion.services.config_service import _get_or_create, obtener_config

    row = _get_or_create(empresa_id)
    dest_dir = _upload_dir(empresa_id, "logos")
    dest = _guardar_imagen(dest_dir / "empresa", file_storage)
    if row.logo_empresa_path:
        old = _path_from_stored(row.logo_empresa_path)
        if old and old.is_file() and old != dest:
            old.unlink(missing_ok=True)
    row.logo_empresa_path = _store_rel(dest)
    row.logo_empresa_bytes = dest.read_bytes()
    row.logo_empresa_mime = _MIME_IMG.get(dest.suffix.lower(), "image/png")
    db.session.commit()
    return obtener_config(empresa_id)


def descargar_logo_empresa(empresa_id: int) -> tuple[Path | bytes, str]:
    row = CapacitacionConfig.query.filter_by(empresa_id=empresa_id).first()
    if not row:
        raise ValueError("Logo no encontrado")
    dest_dir = _upload_dir(empresa_id, "logos", crear=False)
    return _resolver_logo(
        row.logo_empresa_path,
        getattr(row, "logo_empresa_bytes", None),
        getattr(row, "logo_empresa_mime", None),
        dest_dir,
        "empresa",
    )


def eliminar_logo_empresa(empresa_id: int) -> dict:
    from gos.modulos.capacitacion.services.config_service import _get_or_create, obtener_config

    row = _get_or_create(empresa_id)
    dest_dir = _upload_dir(empresa_id, "logos")
    found = _path_from_stored(row.logo_empresa_path) or _canonical_image(dest_dir, "empresa")
    if found and found.is_file():
        found.unlink(missing_ok=True)
    _limpiar_otras_ext(dest_dir / "empresa.png")
    row.logo_empresa_path = None
    row.logo_empresa_bytes = None
    row.logo_empresa_mime = None
    db.session.commit()
    return obtener_config(empresa_id)
