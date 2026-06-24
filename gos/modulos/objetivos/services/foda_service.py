from datetime import date
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename

from sqlalchemy import func

from gos.extensions import db
from gos.modulos.objetivos.models.foda import FODA_TIPOS, FodaDocumento, FodaItem
from gos.modulos.objetivos.services.foda_word_parser import ParsedFodaItem, parse_foda_docx

_PREFIX = {"F": "F", "O": "O", "D": "D", "A": "A"}


def renumerar_codigos_activos(empresa_id: int) -> None:
    """Asigna F-001, F-002… solo a ítems activos (sin huecos por borrados)."""
    inactivos = FodaItem.query.filter_by(empresa_id=empresa_id, activo=False).all()
    for item in inactivos:
        item.codigo = f"Z-{item.id}"
    db.session.flush()

    for tipo, prefix in _PREFIX.items():
        items = (
            FodaItem.query.filter_by(empresa_id=empresa_id, tipo=tipo, activo=True)
            .order_by(FodaItem.orden, FodaItem.id)
            .all()
        )
        for item in items:
            item.codigo = f"{prefix}-T{item.id}"
        db.session.flush()
        for i, item in enumerate(items, start=1):
            item.codigo = f"{prefix}-{i:03d}"


def _siguiente_numero_activo(empresa_id: int, tipo: str) -> int:
    """Cantidad de ítems activos del tipo → el próximo será ese + 1."""
    return (
        FodaItem.query.filter_by(empresa_id=empresa_id, tipo=tipo, activo=True).count()
    )


def _upload_dir(empresa_id: int) -> Path:
    base = Path(current_app.root_path).parent / "storage" / "foda" / str(empresa_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def importar_word(
    empresa_id: int,
    file_storage,
    usuario_nombre: str,
    reemplazar: bool = True,
) -> FodaDocumento:
    filename = secure_filename(file_storage.filename or "documento.docx")
    if not filename.lower().endswith(".docx"):
        raise ValueError("Solo se admiten archivos Word .docx (guardá el .doc como .docx en Word).")

    upload_dir = _upload_dir(empresa_id)
    dest = upload_dir / filename
    file_storage.save(dest)

    parsed: list[ParsedFodaItem] = parse_foda_docx(str(dest))

    if reemplazar:
        FodaItem.query.filter_by(empresa_id=empresa_id, origen="word").delete(
            synchronize_session=False
        )

    doc = FodaDocumento(
        empresa_id=empresa_id,
        nombre_archivo=filename,
        ruta_archivo=str(dest),
        subido_por=usuario_nombre,
        total_items=len(parsed),
    )
    db.session.add(doc)
    db.session.flush()

    db.session.flush()

    for i, item in enumerate(parsed):
        db.session.add(
            FodaItem(
                empresa_id=empresa_id,
                documento_id=doc.id,
                tipo=item.tipo,
                codigo=f"TMP-{doc.id}-{i:04d}",
                descripcion=item.descripcion,
                fecha=date.today(),
                orden=item.orden,
                origen="word",
                activo=True,
            )
        )

    db.session.flush()
    renumerar_codigos_activos(empresa_id)
    db.session.commit()
    return doc


def obtener_matriz(empresa_id: int) -> dict[str, list[FodaItem]]:
    matriz = {t: [] for t in FODA_TIPOS}
    items = (
        FodaItem.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(FodaItem.tipo, FodaItem.orden, FodaItem.id)
        .all()
    )
    for item in items:
        if item.tipo in matriz:
            matriz[item.tipo].append(item)
    return matriz


def ultimo_documento(empresa_id: int) -> FodaDocumento | None:
    return (
        FodaDocumento.query.filter_by(empresa_id=empresa_id)
        .order_by(FodaDocumento.created_at.desc())
        .first()
    )


def obtener_item(empresa_id: int, item_id: int) -> FodaItem | None:
    return FodaItem.query.filter_by(id=item_id, empresa_id=empresa_id, activo=True).first()


def _nuevo_codigo(empresa_id: int, tipo: str) -> str:
    n = _siguiente_numero_activo(empresa_id, tipo) + 1
    return f"{_PREFIX[tipo]}-{n:03d}"


def crear_item_manual(
    empresa_id: int,
    tipo: str,
    descripcion: str,
    area_id: int | None = None,
    responsable_id: int | None = None,
    fecha: date | None = None,
) -> FodaItem:
    if tipo not in FODA_TIPOS:
        raise ValueError("Tipo FODA inválido.")
    desc = descripcion.strip()
    if len(desc) < 3:
        raise ValueError("La descripción debe tener al menos 3 caracteres.")

    max_orden = (
        db.session.query(func.max(FodaItem.orden))
        .filter_by(empresa_id=empresa_id, tipo=tipo, activo=True)
        .scalar()
        or 0
    )
    item = FodaItem(
        empresa_id=empresa_id,
        tipo=tipo,
        codigo=_nuevo_codigo(empresa_id, tipo),
        descripcion=desc,
        area_id=area_id,
        responsable_id=responsable_id,
        fecha=fecha or date.today(),
        orden=max_orden + 1,
        origen="manual",
        activo=True,
    )
    db.session.add(item)
    db.session.flush()
    renumerar_codigos_activos(empresa_id)
    db.session.commit()
    return item


def actualizar_item(
    empresa_id: int,
    item_id: int,
    descripcion: str,
    tipo: str | None = None,
    area_id: int | None = None,
    responsable_id: int | None = None,
    fecha: date | None = None,
    clear_area: bool = False,
    clear_responsable: bool = False,
) -> FodaItem:
    item = obtener_item(empresa_id, item_id)
    if not item:
        raise ValueError("Ítem no encontrado.")
    desc = descripcion.strip()
    if len(desc) < 3:
        raise ValueError("La descripción debe tener al menos 3 caracteres.")

    item.descripcion = desc
    if tipo and tipo in FODA_TIPOS and tipo != item.tipo:
        item.tipo = tipo
        db.session.flush()
        renumerar_codigos_activos(empresa_id)
    if clear_area:
        item.area_id = None
    elif area_id:
        item.area_id = area_id
    if clear_responsable:
        item.responsable_id = None
    elif responsable_id:
        item.responsable_id = responsable_id
    if fecha:
        item.fecha = fecha
    db.session.commit()
    return item


def eliminar_item(empresa_id: int, item_id: int) -> None:
    item = obtener_item(empresa_id, item_id)
    if not item:
        raise ValueError("Ítem no encontrado.")
    item.activo = False
    db.session.flush()
    renumerar_codigos_activos(empresa_id)
    db.session.commit()
