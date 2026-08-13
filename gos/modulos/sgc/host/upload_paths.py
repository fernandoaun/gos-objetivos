"""Rutas de uploads del módulo SGC (aislado bajo instance/uploads/sgi)."""

from __future__ import annotations

from pathlib import Path

from flask import current_app


def uploads_workspace_root() -> Path:
    root = Path(current_app.instance_path) / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_under_upload_roots(rel: Path | str) -> Path | None:
    """Resuelve un path relativo bajo uploads; evita path traversal."""
    rel_path = Path(rel)
    if rel_path.is_absolute():
        candidate = rel_path
    else:
        candidate = (uploads_workspace_root() / rel_path).resolve()
    try:
        candidate.relative_to(uploads_workspace_root().resolve())
    except ValueError:
        return None
    return candidate if candidate.exists() else None
