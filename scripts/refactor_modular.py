"""Migración one-shot: imports y endpoints del módulo objetivos."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OBJ = ROOT / "gos" / "modulos" / "objetivos"

IMPORT_REPLACEMENTS = [
    ("from app.extensions import", "from gos.extensions import"),
    ("from app.models.base import", "from gos.models.base import"),
    ("from app.models.usuario import", "from gos.models.usuario import"),
    ("from app.models import Empresa, PlaneamientoConfig, Usuario", "from gos.models import Empresa, Usuario\nfrom gos.modulos.objetivos.models.catalogos import PlaneamientoConfig"),
    ("from app.models import Empresa, Usuario", "from gos.models import Empresa, Usuario"),
    ("from app.models import Usuario", "from gos.models import Usuario"),
    ("from app.models import Empresa", "from gos.models import Empresa"),
    ("from app.models.catalogos import", "from gos.modulos.objetivos.models.catalogos import"),
    ("from app.models.foda import", "from gos.modulos.objetivos.models.foda import"),
    ("from app.models.kpi import", "from gos.modulos.objetivos.models.kpi import"),
    ("from app.models.objetivo import", "from gos.modulos.objetivos.models.objetivo import"),
    ("from app.models import", "from gos.modulos.objetivos.models import"),
    ("from app.services.", "from gos.modulos.objetivos.services."),
    ("from app.blueprints.", "from gos.modulos.objetivos.blueprints."),
    ("from app.utils.", "from gos.modulos.objetivos.utils."),
    ("from app.version import", "from gos.modulos.objetivos.version import"),
    ("from app import create_app", "from gos import create_app"),
    ("from app.config import", "from gos.config import"),
    ("import app.", "import gos.modulos.objetivos."),
]

BLUEPRINT_REPLACEMENTS = [
    ('Blueprint("main"', 'Blueprint("objetivos.main"'),
    ('Blueprint("dashboard"', 'Blueprint("objetivos.dashboard"'),
    ('Blueprint("foda"', 'Blueprint("objetivos.foda"'),
    ('Blueprint("objetivos"', 'Blueprint("objetivos.estrategicos"'),
    ('Blueprint("kpis"', 'Blueprint("objetivos.kpis"'),
    ('Blueprint("metas"', 'Blueprint("objetivos.metas"'),
    ('Blueprint("seguimiento"', 'Blueprint("objetivos.seguimiento"'),
    ('Blueprint("planes"', 'Blueprint("objetivos.planes"'),
    ('Blueprint("reportes"', 'Blueprint("objetivos.reportes"'),
    ('Blueprint("configuracion"', 'Blueprint("objetivos.configuracion"'),
    ('Blueprint("api"', 'Blueprint("objetivos.api"'),
]

ENDPOINT_REPLACEMENTS = [
    ('url_for("dashboard.', 'url_for("objetivos.dashboard.'),
    ("url_for('dashboard.", "url_for('objetivos.dashboard."),
    ('url_for("foda.', 'url_for("objetivos.foda.'),
    ("url_for('foda.", "url_for('objetivos.foda."),
    ('url_for("objetivos.', 'url_for("objetivos.estrategicos.'),
    ("url_for('objetivos.", "url_for('objetivos.estrategicos."),
    ('url_for("kpis.', 'url_for("objetivos.kpis.'),
    ("url_for('kpis.", "url_for('objetivos.kpis."),
    ('url_for("reportes.', 'url_for("objetivos.reportes.'),
    ("url_for('reportes.", "url_for('objetivos.reportes."),
    ('url_for("configuracion.', 'url_for("objetivos.configuracion.'),
    ("url_for('configuracion.", "url_for('objetivos.configuracion."),
    ('"dashboard.index"', '"objetivos.dashboard.index"'),
    ('"foda.index"', '"objetivos.foda.index"'),
    ('"objetivos.index"', '"objetivos.estrategicos.index"'),
    ('"kpis.index"', '"objetivos.kpis.index"'),
    ('"reportes.index"', '"objetivos.reportes.index"'),
    ('"configuracion.index"', '"objetivos.configuracion.index"'),
    ("endpoint': 'dashboard.", "endpoint': 'objetivos.dashboard."),
    ("endpoint': 'foda.", "endpoint': 'objetivos.foda."),
    ("endpoint': 'objetivos.", "endpoint': 'objetivos.estrategicos."),
    ("endpoint': 'kpis.", "endpoint': 'objetivos.kpis."),
    ("endpoint': 'reportes.", "endpoint': 'objetivos.reportes."),
    ("endpoint': 'configuracion.", "endpoint': 'objetivos.configuracion."),
]

STATIC_REPLACEMENTS = [
    ("url_for('static', filename='css/", "url_for('objetivos.static', filename='css/"),
    ('url_for("static", filename="css/', 'url_for("objetivos.static", filename="css/'),
    ("url_for('static', filename='js/foda", "url_for('objetivos.static', filename='js/foda"),
    ('url_for("static", filename="js/foda', 'url_for("objetivos.static", filename="js/foda'),
]


def transform(text: str, path: Path) -> str:
    for old, new in IMPORT_REPLACEMENTS:
        text = text.replace(old, new)
    for old, new in BLUEPRINT_REPLACEMENTS:
        text = text.replace(old, new)
    for old, new in ENDPOINT_REPLACEMENTS:
        text = text.replace(old, new)
    if path.suffix in {".html", ".js"} and "objetivos/static" not in text:
        for old, new in STATIC_REPLACEMENTS:
            if "theme.css" in text or "layout.css" in text or "theme-toggle" in text or "app.js" in text:
                continue
            text = text.replace(old, new)
    return text


def main() -> None:
    targets = list(OBJ.rglob("*"))
    targets += list((ROOT / "tests").rglob("*.py"))
    targets += [
        ROOT / "wsgi.py",
        ROOT / "run.py",
        ROOT / "scripts" / "init_db.py",
        ROOT / "scripts" / "seed_demo.py",
        ROOT / "scripts" / "ensure_admin.py",
        ROOT / "scripts" / "render_start.py",
        ROOT / "scripts" / "renumerar_foda.py",
    ]
    for path in targets:
        if not path.is_file() or path.suffix not in {".py", ".html", ".js"}:
            continue
        if path.name == "refactor_modular.py":
            continue
        original = path.read_text(encoding="utf-8")
        updated = transform(original, path)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            print(f"updated: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
