"""URLs absolutas para mails de workflow SGC."""

from __future__ import annotations

from typing import Any

from flask import url_for


def public_abs_url(app: Any, endpoint: str, **values: Any) -> str:
    try:
        with app.app_context():
            return url_for(endpoint, _external=True, **values)
    except Exception:
        return url_for(endpoint, _external=False, **values)
