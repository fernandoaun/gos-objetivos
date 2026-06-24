"""Corrige nombres de blueprint: Flask 3 no permite puntos."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPLACEMENTS = [
    ("objetivos.estrategicos", "objetivos_estrategicos"),
    ("objetivos.configuracion", "objetivos_configuracion"),
    ("objetivos.seguimiento", "objetivos_seguimiento"),
    ("objetivos.dashboard", "objetivos_dashboard"),
    ("objetivos.reportes", "objetivos_reportes"),
    ("objetivos.static", "objetivos_static"),
    ("objetivos.planes", "objetivos_planes"),
    ("objetivos.main", "objetivos_main"),
    ("objetivos.foda", "objetivos_foda"),
    ("objetivos.kpis", "objetivos_kpis"),
    ("objetivos.metas", "objetivos_metas"),
    ("objetivos.api", "objetivos_api"),
]

for folder in (ROOT / "gos", ROOT / "tests"):
    for path in folder.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".html", ".js"}:
            continue
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in REPLACEMENTS:
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            print(path.relative_to(ROOT))
