"""Validación mínima de emails (compat QDV)."""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


def normalize_validate_email(raw: str | None) -> str | None:
    s = (raw or "").strip().lower()
    if not s or not _EMAIL_RE.match(s):
        return None
    return s
