"""Auditoría liviana SGC (log app; no escribe tablas de otros módulos)."""

from __future__ import annotations

import logging
from typing import Any

_logger = logging.getLogger("gos.sgc.audit")


def record_event(
    *,
    action: str | None = None,
    entity: str | None = None,
    entity_id: Any = None,
    actor_id: Any = None,
    detail: Any = None,
    **kwargs: Any,
) -> None:
    _logger.info(
        "sgc_audit action=%s entity=%s entity_id=%s actor_id=%s detail=%s extra=%s",
        action,
        entity,
        entity_id,
        actor_id,
        detail,
        kwargs or None,
    )
