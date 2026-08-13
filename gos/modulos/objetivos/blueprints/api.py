import tempfile
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from gos import env
from gos.modulos.objetivos.version import APP_VERSION

bp = Blueprint("objetivos_api", __name__)


def _import_auth_ok() -> bool:
    provided = (request.headers.get("X-Import-Secret") or request.args.get("secret") or "").strip()
    return env.import_auth_ok(provided)


@bp.route("/health")
def health():
    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    backend = "postgresql" if uri.startswith("postgres") else "sqlite"
    payload = {
        "ok": True,
        "service": "gos-objetivos",
        "version": APP_VERSION,
        "features": ["foda-word", "foda-crud", "foda-pdf"],
        "database_backend": backend,
    }
    if request.args.get("db") == "1":
        try:
            from gos.modulos.objetivos.models import FodaItem, KpiIndicador, Objetivo
            from gos.models import Usuario

            payload["db"] = {
                "backend": backend,
                "usuarios": Usuario.query.count(),
                "foda_items": FodaItem.query.count(),
                "objetivos": Objetivo.query.count(),
                "kpi_indicadores": KpiIndicador.query.count(),
            }
        except Exception as exc:
            current_app.logger.exception("health db check failed")
            payload["ok"] = False
            payload["db_error"] = f"{type(exc).__name__}: {exc}"
            return jsonify(payload), 500
    return jsonify(payload)


@bp.route("/admin/import-status")
def import_status():
    from gos.modulos.objetivos.models import FodaItem, KpiIndicador, Objetivo
    from gos.models import Perfil, Usuario

    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    try:
        return jsonify({
            "ok": True,
            "import_secret_configured": bool(env.import_secret()),
            "database_backend": "postgresql" if uri.startswith("postgres") else "sqlite",
            "db": {
                "foda_items": FodaItem.query.count(),
                "objetivos": Objetivo.query.count(),
                "kpi_indicadores": KpiIndicador.query.count(),
                "usuarios": Usuario.query.count(),
                "perfiles": Perfil.query.count(),
            },
        })
    except Exception as exc:
        current_app.logger.exception("import-status failed")
        return jsonify({
            "ok": False,
            "import_secret_configured": bool(env.import_secret()),
            "database_backend": "postgresql" if uri.startswith("postgres") else "sqlite",
            "error": f"{type(exc).__name__}: {exc}",
        }), 500


@bp.route("/admin/upsert-perfiles", methods=["POST"])
def upsert_perfiles():
    """Restaura/actualiza perfiles sin tocar el resto de la base (seguro post-wipe)."""
    if not _import_auth_ok():
        return jsonify({
            "ok": False,
            "error": "No autorizado. Configurá GOS_IMPORT_SECRET y enviá X-Import-Secret.",
        }), 403

    from gos.models import Empresa
    from gos.services import perfil_service

    payload = request.get_json(silent=True) or {}
    perfiles = payload.get("perfiles")
    if perfiles is None:
        perfiles = list(perfil_service.PERFILES_BASE)
    if not isinstance(perfiles, list):
        return jsonify({"ok": False, "error": "perfiles debe ser una lista"}), 400

    empresa = Empresa.query.order_by(Empresa.id).first()
    if not empresa:
        return jsonify({"ok": False, "error": "No hay empresa en la base"}), 400

    try:
        result = perfil_service.upsert_perfiles_empresa(empresa.id, perfiles)
        return jsonify({
            "ok": True,
            "empresa_id": empresa.id,
            **result,
            "perfiles": perfil_service.exportar_perfiles_empresa(empresa.id),
        })
    except Exception as exc:
        current_app.logger.exception("upsert-perfiles failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/admin/export-tables", methods=["GET", "POST"])
def export_tables():
    """Exporta tablas (JSON) para bajar datos de Render → local sin wipe."""
    if not _import_auth_ok():
        return jsonify({
            "ok": False,
            "error": "No autorizado. Configurá GOS_IMPORT_SECRET y enviá X-Import-Secret.",
        }), 403

    from sqlalchemy import inspect, text

    from gos.extensions import db
    from gos.modulos.objetivos.services.import_service import TABLES

    payload = request.get_json(silent=True) or {}
    requested = payload.get("tables") or request.args.getlist("table")
    if not requested:
        requested = [
            "sectores",
            "areas",
            "responsables",
            "objetivos",
            "kpi_indicadores",
            "foda_documentos",
            "foda_items",
            "dafo_tareas",
            "planeamiento_config",
        ]
    allowed = set(TABLES)
    tables = [t for t in requested if t in allowed]
    if not tables:
        return jsonify({"ok": False, "error": "Ninguna tabla válida"}), 400

    try:
        existing = set(inspect(db.engine).get_table_names())
        out: dict[str, list] = {}
        counts: dict[str, int] = {}
        with db.engine.connect() as conn:
            for table in tables:
                if table not in existing:
                    out[table] = []
                    counts[table] = 0
                    continue
                rows = conn.execute(text(f'SELECT * FROM "{table}"')).mappings().all()
                serializable = []
                for row in rows:
                    item = {}
                    for key, value in dict(row).items():
                        if hasattr(value, "isoformat"):
                            item[key] = value.isoformat()
                        elif isinstance(value, (bytes, memoryview)):
                            item[key] = bytes(value).hex()
                        else:
                            item[key] = value
                    serializable.append(item)
                out[table] = serializable
                counts[table] = len(serializable)
        return jsonify({"ok": True, "counts": counts, "tables": out})
    except Exception as exc:
        current_app.logger.exception("export-tables failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/admin/import-tables", methods=["POST"])
def import_tables():
    """Importa tablas puntuales desde JSON (sin subir el SQLite completo)."""
    if not _import_auth_ok():
        return jsonify({
            "ok": False,
            "error": "No autorizado. Configurá GOS_IMPORT_SECRET y enviá X-Import-Secret.",
        }), 403

    payload = request.get_json(silent=True) or {}
    tables = payload.get("tables")
    if not isinstance(tables, dict) or not tables:
        return jsonify({"ok": False, "error": "tables debe ser un objeto {nombre: [filas]}"}), 400
    allow_cap = bool(payload.get("allow_cap_overwrite"))

    try:
        from gos.modulos.capacitacion.services.backup_service import snapshot_capacitacion
        from gos.modulos.objetivos.services.import_service import CAP_TABLES, importar_tablas_json

        if any(t in CAP_TABLES for t in tables):
            try:
                snapshot_capacitacion(motivo="pre-import-tables")
            except Exception:
                current_app.logger.exception("snapshot pre-import-tables falló")

        target_url = current_app.config["SQLALCHEMY_DATABASE_URI"]
        counts = importar_tablas_json(
            tables, target_url, allow_cap_overwrite=allow_cap
        )
        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        return jsonify({
            "ok": True,
            "database_backend": "postgresql" if uri.startswith("postgres") else "sqlite",
            "imported": counts,
            "cap_overwrite": allow_cap,
        })
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("import-tables failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.route("/admin/import-db", methods=["POST"])
def import_db():
    """Restaura backup SQLite en la base que usa el servicio web."""
    if not _import_auth_ok():
        return jsonify({
            "ok": False,
            "error": "No autorizado. Configurá GOS_IMPORT_SECRET y enviá X-Import-Secret.",
        }), 403

    upload = request.files.get("database")
    if not upload or not upload.filename:
        return jsonify({"ok": False, "error": "Falta archivo database"}), 400
    allow_cap = str(request.form.get("allow_cap_overwrite") or "").strip().lower() in (
        "1",
        "true",
        "si",
        "yes",
    )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            upload.save(tmp.name)
            tmp_path = Path(tmp.name)

        from gos.modulos.capacitacion.services.backup_service import snapshot_capacitacion
        from gos.modulos.objetivos.services.import_service import importar_sqlite

        try:
            snapshot_capacitacion(motivo="pre-import-db")
        except Exception:
            current_app.logger.exception("snapshot pre-import-db falló")

        target_url = current_app.config["SQLALCHEMY_DATABASE_URI"]
        counts = importar_sqlite(
            tmp_path, target_url, allow_cap_overwrite=allow_cap
        )
        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        return jsonify({
            "ok": True,
            "database_backend": "postgresql" if uri.startswith("postgres") else "sqlite",
            "imported": {k: v for k, v in counts.items() if v},
            "cap_overwrite": allow_cap,
        })
    except Exception as exc:
        current_app.logger.exception("import-db failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
