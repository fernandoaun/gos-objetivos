from __future__ import annotations

import json

from gos.extensions import db
from gos.modulos.capacitacion.models.config import CapacitacionConfig

DEFAULT_DIAS_PROXIMO_VENCER = 30
DEFAULT_DIAS_ENCUENTRO_PROXIMO = 7
DEFAULT_PCT_CUMPLIMIENTO = 80
DEFAULT_PERIODOS_VIGENCIA = [
    {"meses": 6, "label": "6 meses"},
    {"meses": 12, "label": "1 año"},
    {"meses": 18, "label": "18 meses"},
    {"meses": 24, "label": "2 años"},
    {"meses": 36, "label": "3 años"},
]


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(e).strip().lower() for e in data if e and str(e).strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    return [e.strip().lower() for e in raw.split(",") if e.strip()]


def _parse_json_map(raw: str | None) -> dict[str, list[str]]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            result: dict[str, list[str]] = {}
            for k, v in data.items():
                if isinstance(v, list):
                    result[str(k)] = [str(e).strip().lower() for e in v if e and str(e).strip()]
                elif v:
                    result[str(k)] = [str(v).strip().lower()]
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    return {}


def _dump_json_list(items: list | None) -> str | None:
    if not items:
        return None
    cleaned = [str(e).strip().lower() for e in items if e and str(e).strip()]
    return json.dumps(cleaned) if cleaned else None


def _dump_json_map(data: dict | None) -> str | None:
    if not data:
        return None
    cleaned: dict[str, list[str]] = {}
    for k, v in data.items():
        if isinstance(v, list):
            emails = [str(e).strip().lower() for e in v if e and str(e).strip()]
            if emails:
                cleaned[str(k)] = emails
        elif v:
            cleaned[str(k)] = [str(v).strip().lower()]
    return json.dumps(cleaned) if cleaned else None


def _parse_periodos_vigencia(raw: str | None) -> list[dict]:
    if not raw:
        return list(DEFAULT_PERIODOS_VIGENCIA)
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return list(DEFAULT_PERIODOS_VIGENCIA)
        result = []
        seen = set()
        for item in data:
            if isinstance(item, dict):
                meses = int(item.get("meses") or 0)
                label = (item.get("label") or "").strip()
            else:
                meses = int(item)
                label = ""
            if meses < 1 or meses in seen:
                continue
            seen.add(meses)
            if not label:
                label = _label_periodo_vigencia(meses)
            result.append({"meses": meses, "label": label})
        return result or list(DEFAULT_PERIODOS_VIGENCIA)
    except (json.JSONDecodeError, TypeError, ValueError):
        return list(DEFAULT_PERIODOS_VIGENCIA)


def _label_periodo_vigencia(meses: int) -> str:
    if meses % 12 == 0 and meses >= 12:
        anos = meses // 12
        return f"{anos} año" if anos == 1 else f"{anos} años"
    return f"{meses} meses"


def _dump_periodos_vigencia(periodos: list | None) -> str | None:
    if not periodos:
        return None
    cleaned = []
    seen = set()
    for item in periodos:
        if isinstance(item, dict):
            meses = int(item.get("meses") or 0)
            label = (item.get("label") or "").strip() or _label_periodo_vigencia(meses)
        else:
            meses = int(item)
            label = _label_periodo_vigencia(meses)
        if meses < 1 or meses > 120 or meses in seen:
            continue
        seen.add(meses)
        cleaned.append({"meses": meses, "label": label})
    return json.dumps(sorted(cleaned, key=lambda x: x["meses"])) if cleaned else None


def _defaults() -> dict:
    return {
        "dias_proximo_vencer": DEFAULT_DIAS_PROXIMO_VENCER,
        "dias_encuentro_proximo": DEFAULT_DIAS_ENCUENTRO_PROXIMO,
        "pct_cumplimiento_minimo": DEFAULT_PCT_CUMPLIMIENTO,
        "notif_email_activo": False,
        "notif_vencimiento": True,
        "notif_obligatorio": True,
        "notif_curso_proximo": True,
        "emails_destinatarios": [],
        "emails_por_sector": {},
        "emails_por_rol": {},
        "ultimo_envio_notif": None,
        "periodos_vigencia": list(DEFAULT_PERIODOS_VIGENCIA),
    }


def _row_to_dict(row: CapacitacionConfig) -> dict:
    return {
        "dias_proximo_vencer": row.dias_proximo_vencer,
        "dias_encuentro_proximo": row.dias_encuentro_proximo,
        "pct_cumplimiento_minimo": row.pct_cumplimiento_minimo,
        "notif_email_activo": row.notif_email_activo,
        "notif_vencimiento": row.notif_vencimiento,
        "notif_obligatorio": row.notif_obligatorio,
        "notif_curso_proximo": row.notif_curso_proximo,
        "emails_destinatarios": _parse_json_list(row.emails_destinatarios),
        "emails_por_sector": _parse_json_map(row.emails_por_sector),
        "emails_por_rol": _parse_json_map(row.emails_por_rol),
        "ultimo_envio_notif": row.ultimo_envio_notif.isoformat() if row.ultimo_envio_notif else None,
        "periodos_vigencia": _parse_periodos_vigencia(row.periodos_vigencia),
    }


def obtener_config(empresa_id: int) -> dict:
    row = CapacitacionConfig.query.filter_by(empresa_id=empresa_id).first()
    if not row:
        return _defaults()
    return _row_to_dict(row)


def _get_or_create(empresa_id: int) -> CapacitacionConfig:
    row = CapacitacionConfig.query.filter_by(empresa_id=empresa_id).first()
    if not row:
        row = CapacitacionConfig(empresa_id=empresa_id)
        db.session.add(row)
    return row


def dias_proximo_vencer(empresa_id: int) -> int:
    return obtener_config(empresa_id)["dias_proximo_vencer"]


def dias_encuentro_proximo(empresa_id: int) -> int:
    return obtener_config(empresa_id)["dias_encuentro_proximo"]


def pct_cumplimiento_minimo(empresa_id: int) -> int:
    return obtener_config(empresa_id)["pct_cumplimiento_minimo"]


def listar_periodos_vigencia(empresa_id: int) -> list[dict]:
    return obtener_config(empresa_id)["periodos_vigencia"]


def agregar_periodo_vigencia(empresa_id: int, meses: int, label: str | None = None) -> list[dict]:
    meses = int(meses)
    if meses < 1 or meses > 120:
        raise ValueError("El período debe estar entre 1 y 120 meses")
    row = _get_or_create(empresa_id)
    periodos = _parse_periodos_vigencia(row.periodos_vigencia)
    if any(p["meses"] == meses for p in periodos):
        raise ValueError("Ese período ya existe en la lista")
    periodos.append({"meses": meses, "label": (label or "").strip() or _label_periodo_vigencia(meses)})
    periodos.sort(key=lambda x: x["meses"])
    row.periodos_vigencia = _dump_periodos_vigencia(periodos)
    db.session.commit()
    return periodos


def guardar_config(empresa_id: int, data: dict) -> dict:
    dias_v = data.get("dias_proximo_vencer")
    dias_e = data.get("dias_encuentro_proximo")
    pct = data.get("pct_cumplimiento_minimo")
    if dias_v is not None:
        dias_v = int(dias_v)
        if dias_v < 1 or dias_v > 365:
            raise ValueError("dias_proximo_vencer debe estar entre 1 y 365")
    if dias_e is not None:
        dias_e = int(dias_e)
        if dias_e < 1 or dias_e > 90:
            raise ValueError("dias_encuentro_proximo debe estar entre 1 y 90")
    if pct is not None:
        pct = int(pct)
        if pct < 0 or pct > 100:
            raise ValueError("pct_cumplimiento_minimo debe estar entre 0 y 100")

    row = _get_or_create(empresa_id)
    if dias_v is not None:
        row.dias_proximo_vencer = dias_v
    if dias_e is not None:
        row.dias_encuentro_proximo = dias_e
    if pct is not None:
        row.pct_cumplimiento_minimo = pct
    if "notif_email_activo" in data:
        row.notif_email_activo = bool(data["notif_email_activo"])
    if "notif_vencimiento" in data:
        row.notif_vencimiento = bool(data["notif_vencimiento"])
    if "notif_obligatorio" in data:
        row.notif_obligatorio = bool(data["notif_obligatorio"])
    if "notif_curso_proximo" in data:
        row.notif_curso_proximo = bool(data["notif_curso_proximo"])
    if "emails_destinatarios" in data:
        row.emails_destinatarios = _dump_json_list(data["emails_destinatarios"])
    if "emails_por_sector" in data:
        row.emails_por_sector = _dump_json_map(data["emails_por_sector"])
    if "emails_por_rol" in data:
        row.emails_por_rol = _dump_json_map(data["emails_por_rol"])
    if "periodos_vigencia" in data:
        row.periodos_vigencia = _dump_periodos_vigencia(data["periodos_vigencia"])
    db.session.commit()
    return obtener_config(empresa_id)
